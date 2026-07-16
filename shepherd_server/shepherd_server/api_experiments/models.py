import copy
import shutil
import subprocess
from datetime import datetime
from datetime import timedelta
from io import StringIO
from pathlib import Path
from uuid import UUID
from uuid import uuid4

import pymongo
from beanie import Document
from beanie import Link
from beanie.operators import In
from fastapi import UploadFile
from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field
from shepherd_core.data_models.base.timezone import local_now
from shepherd_core.data_models.base.timezone import local_tz
from shepherd_core.data_models.experiment import Experiment
from shepherd_core.reader import Reader as CoreReader
from typing_extensions import Self
from typing_extensions import deprecated

from shepherd_server.api_accounts.models import User
from shepherd_server.api_accounts.models import UserRole
from shepherd_server.config import server_config
from shepherd_server.logger import log


def obtain_access_permissions(path: Path) -> None:
    ret = subprocess.run(  # noqa: S603
        ["/usr/bin/sudo", "/usr/bin/chmod", "a+rw", "-R", path.as_posix()],
        capture_output=False,
        timeout=20,
        check=False,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    ).returncode
    if ret != 0:
        log.warning("Changing permission denied for %s", path)


class ReplyData(BaseModel):
    exited: int  # state of process: -1: still active, 0: exited without error, 1: exited with error
    stdout: str
    stderr: str


class ErrorData(BaseModel):
    # status & error - log
    observers_requested: list[str] = []
    observers_online: list[str] = []
    observers_offline: list[str] = []

    observers_output: dict[str, ReplyData] = {}
    observers_had_data: dict[str, bool] = {}

    scheduler_error: str | None = None
    scheduler_log: str | None = None  # for admin

    def get_terminal_output(self, *, only_faulty: bool = False) -> list[UploadFile]:
        """Log output-results of shell commands."""
        files = []
        # sort dict by key first
        replies = dict(sorted(self.observers_output.items()))
        for hostname, reply in replies.items():
            if hostname not in self.observers_requested:
                continue
            had_error = abs(reply.exited) != 0 or not self.observers_had_data.get(hostname, False)
            if only_faulty and not had_error:
                continue
            string = ""
            if len(reply.stdout) > 0:
                string += f"\n************** {hostname} - stdout **************\n"
                string += reply.stdout
            if len(reply.stderr) > 0:
                string += f"\n~~~~~~~~~~~~~~ {hostname} - stderr ~~~~~~~~~~~~~~\n"
                string += reply.stderr
            string += f"\nExit-code of {hostname} = {reply.exited}\n"
            files.append(
                UploadFile(
                    filename=f"{hostname}{'_error' if reply.exited != 0 else ''}.log",
                    file=StringIO(string),
                )
            )
        if self.scheduler_log is not None and len(self.scheduler_log) > 0:
            # TODO: only admin & only if faulty
            files.append(UploadFile(filename="scheduler.log", file=StringIO(self.scheduler_log)))
        return files

    @property
    def max_exit_code(self) -> int:
        # note that missing (but requested) observers don't count here
        obs_exited = {obs: abs(reply.exited) for obs, reply in self.observers_output.items()}
        return max([0] + [obs_exited.get(obs, 0) for obs in self.observers_requested])

    @property
    def has_missing_data(self) -> bool:
        return not all(self.observers_had_data.get(obs, False) for obs in self.observers_requested)

    @property
    def missing_observers(self) -> list[str]:
        return sorted(set(self.observers_requested) - set(self.observers_online))


class ResultData(ErrorData):
    observer_paths: dict[str, Path] | None = None
    """Observer paths are used as future (will be filled by observers)
    """

    result_paths: dict[str, Path] | None = None
    result_size: int = 0
    content_paths: dict[str, Path] | None = None
    """
    Content-path is currently the parent of result-path.
    Besides the H5-files, it contains firmware and meta-data.
    """

    async def update_size(self) -> None:
        _size = 0
        if isinstance(self.result_paths, dict):
            for path in self.result_paths.values():
                if path.exists() and path.is_file():
                    _size += path.stat().st_size
                else:
                    log.warning(f"file '{path}' does not exist after the experiment")
        self.result_size = _size
        if isinstance(self, Document):
            await self.save_changes()
        else:
            raise TypeError("ResultData-Type was used outside of WebExperiment-Context")

    async def update_result(self, paths: dict[str, Path] | None = None) -> None:
        if paths is None:
            if self.observer_paths is not None:
                paths = self.observer_paths
            else:
                raise ValueError("Update_result() needs data")
        self.result_paths = copy.deepcopy(paths)
        # TODO: hardcoded bending of observer to server path-structure
        #       from sheep-path: /var/shepherd/experiments/xp_name
        #       to server-path:  /var/shepherd/experiments/sheep_name/xp_name
        for observer in paths:
            path_obs = paths[observer].absolute()
            if not path_obs.is_relative_to("/var/shepherd/experiments"):
                log.error("Path outside of experiment-location? %s", path_obs.as_posix())
                self.result_paths.pop(observer)
                continue
            try:
                path_obs_exists = path_obs.exists()
            except PermissionError:
                path_obs_exists = False
            if path_obs_exists:
                log.warning("Observer-Path should not exist on server! %s", path_obs.as_posix())
            path_rel = path_obs.relative_to("/var/shepherd/experiments")
            path_srv = Path("/var/shepherd/experiments") / observer / path_rel
            obtain_access_permissions(path_srv.parent)
            # TODO: switch to root-xp-path and run recursively? that output in the logs is bad
            try:
                path_srv_exists = path_srv.exists()

            except PermissionError:
                log.error("Permission-Error on Server-Path -> will skip!")
                path_srv_exists = False
            if not path_srv_exists:
                log.error("Server-Path must exist on server! %s", path_srv.as_posix())
                self.result_paths.pop(observer)
                continue
            self.result_paths[observer] = path_srv
        for observer in self.observers_requested:
            path = self.result_paths.get(observer)
            self.observers_had_data[observer] = path is not None and path.exists()

        if isinstance(self.result_paths, dict) and len(self.result_paths) > 0:
            self.content_paths = {key: path.parent for key, path in self.result_paths.items()}
            await self.update_size()
        else:
            log.warning("Skipped adding empty content path list")
            self.content_paths = None
            self.result_paths = None
        if isinstance(self, Document):
            await self.save_changes()
        else:
            raise TypeError("ResultData-Type was used outside of WebExperiment-Context")

    async def delete_content(self) -> None:
        # TODO: just overwrite default delete-method?
        if isinstance(self.result_paths, dict):
            # removing large result-files first
            for result_file in self.result_paths.values():
                if result_file.exists() and result_file.is_file():
                    result_file.unlink()
            self.result_paths = None
        if isinstance(self.content_paths, dict):
            # remove leftover firmware and meta-data
            for content_dir in self.content_paths.values():
                shutil.rmtree(content_dir, ignore_errors=True)
            self.content_paths = None
        if isinstance(self, Document):
            await self.save_changes()
        else:
            raise TypeError("ResultData-Type was used outside of WebExperiment-Context")


class WebExperiment(Document, ResultData, ErrorData):
    id: UUID = Field(default_factory=uuid4)
    owner: Link[User] | None = None
    experiment: Experiment

    created_at: datetime = Field(default_factory=local_now)

    requested_execution_at: datetime | None = None
    """
    None, if the experiment should not be executed.
    Set by the API to current wall-clock time when the user requests the experiment
    to be executed.
    This is NOT the time when the experiment should be run!
    """

    started_at: datetime | None = None
    """
    None, when the experiment is not yet prepared on the testbed.
    Set to current wall-clock time when the web runner picks experiment and
    starts preparation on the testbed.
    """

    executed_at: datetime | None = None
    """
    None, when the experiment is not yet executed.
    Set to current wall-clock time when the actual experiment starts.
    """

    finished_at: datetime | None = None
    """
    None, when the experiment is not yet finished (still executing or not yet started).
    Set to current wall-clock time by the web runner when the testbed finished execution.
    """

    class Settings:  # allows using .save_changes()
        use_state_management = True
        state_management_save_previous = True
        validate_on_save = True

    @classmethod
    async def get_by_id(cls, experiment_id: UUID) -> None | Self:
        return await cls.find_one(
            cls.id == experiment_id,
            fetch_links=True,
            # lazy_parse only recommended when not changing & saving
        )

    @classmethod
    @deprecated("Usage discouraged, as each element may be 1 - 10 MiB in size.")
    async def get_by_user(cls, user: User) -> list[Self]:
        return await (
            cls.find(
                cls.owner.email == user.email,
                fetch_links=True,
                # lazy_parse only recommended when not changing & saving
            )
            .sort((cls.created_at, pymongo.ASCENDING))
            .to_list()
        )

    @classmethod
    async def get_all_states(cls, user: User | None = None) -> dict[UUID, str]:
        """Fetch all states of existing experiments.

        - removed .sort((cls.created_at, pymongo.ASCENDING)) as order was discarded by fastapi
        """
        if user is None:
            data = await cls.all(lazy_parse=True).to_list()
        else:
            data = await cls.find(
                cls.owner.email == user.email,
                fetch_links=True,
                lazy_parse=True,
            ).to_list()
        return {date.id: date.state for date in data}

    @classmethod
    async def get_storage(cls, user: User) -> int:
        # TODO: performance optimization
        size = await cls.find(
            cls.owner.email == user.email,
            fetch_links=True,
            lazy_parse=True,
        ).sum(cls.result_size)
        return int(size) if size else 0

    @classmethod
    async def get_next_scheduling(cls, *, only_elevated: bool = False) -> None | Self:
        """
        Finds the WebExperiment with the oldest scheduling_at datetime,
        that has not been executed yet (status less than active).
        """
        roles_allow = [UserRole.admin, UserRole.elevated] if only_elevated else list(UserRole)
        next_experiments = (
            await cls.find(
                cls.requested_execution_at != None,  # noqa: E711 beanie cannot handle 'is not None'
                cls.started_at == None,  # noqa: E711
                In(cls.owner.role, roles_allow),
                fetch_links=True,
            )
            .sort((cls.requested_execution_at, pymongo.ASCENDING))
            .limit(1)
            .to_list()
        )
        if len(next_experiments) > 0:
            return next_experiments[0]
        return None

    @classmethod
    async def has_scheduled_by_user(cls, user: User) -> bool:
        xp_ = (
            await cls.find(
                cls.requested_execution_at != None,  # noqa: E711 beanie cannot handle 'is not None'
                cls.started_at == None,  # noqa: E711
                cls.owner.email == user.email,
                fetch_links=True,
                lazy_parse=True,
            )
            .limit(1)
            .to_list()
        )
        return len(xp_) > 0

    @classmethod
    async def reset_stuck_items(cls) -> None:
        """Find and reset scheduled, but unfinished experiments."""
        stuck_xps = await cls.find(
            cls.finished_at == None,  # noqa: E711 beanie cannot handle 'is not None'
            cls.started_at != None,  # noqa: E711
            # used to also filter for scheduler_error==None, but finished_at is enough
            fetch_links=True,
            # lazy_parse only recommended when not changing & saving
        ).to_list()
        for _xp in stuck_xps:
            log.info("Resetting experiment: %s", _xp.id)
            _xp.started_at = None
            await _xp.save_changes()

    @classmethod
    async def prune(cls, users: list[User] | None = None, *, dry_run: bool = True) -> int:
        # TODO: find xp with missing link to user (zombies)
        wxp_ids_2_prune = []

        # fetch experiments by user
        if users is not None:
            for user in users:
                wxp_ids_2_prune += list((await cls.get_all_states(user)).keys())

        # get oldest XP of users over quota
        users_all = await User.find_all(lazy_parse=True).to_list()
        wxp_date_limit = local_now() - server_config.age_min_experiment
        for user in users_all:
            wxp_ids_user = await cls.get_all_states(user)
            storage_user = await cls.get_storage(user)
            for wxp_id in wxp_ids_user:
                wxp = await cls.get_by_id(wxp_id)
                if not isinstance(wxp, WebExperiment):
                    log.error("XP %s could not be pruned (was not found)", wxp_id)
                    continue
                if wxp.created_at >= wxp_date_limit:
                    continue
                if storage_user >= user.quota_storage:
                    wxp_ids_2_prune.append(wxp.id)
                    storage_user -= wxp.result_size

        # get xp exceeding max age
        wxp_ids_2_prune += await cls.find(
            cls.created_at <= local_now() - server_config.age_max_experiment,
            fetch_links=True,
        ).to_list()

        # calculate size of experiments
        wxp_ids_2_prune = set(wxp_ids_2_prune)

        size_total = 0
        # was: sum((await cls.get_by_id(xp_id)).result_size for xp_id in xp_ids_2_prune)
        for wxp_id in wxp_ids_2_prune:
            wxp = await cls.get_by_id(wxp_id)
            if not isinstance(wxp, WebExperiment):
                continue
            size_total += wxp.result_size

        if dry_run:
            log.info("Pruning old experiments could free: %d MiB", size_total / (2**20))
        else:
            for wxp_id in wxp_ids_2_prune:
                wxp = await cls.get_by_id(wxp_id)
                if not isinstance(wxp, WebExperiment):
                    log.error("XP %s could not be deleted (was not found)", wxp_id)
                    continue
                log.debug(" -> deleting experiment %s", wxp.experiment.name)
                await ExperimentStats.update_with(wxp, to_be_deleted=True)
                await wxp.delete_content()
                await wxp.delete()
            log.info("Pruning old experiments freed: %d MiB", size_total / (2**20))
        return size_total

    @property
    def state(self) -> str:
        # TODO: add deleted?
        if self.finished_at is not None:
            if self.had_errors:
                return "failed"
            return "finished"
        if self.executed_at is not None and self.executed_at < datetime.now(
            tz=self.executed_at.tzinfo
        ):
            # the code above looks weird, but default beanie does not save TZ, so we adapt
            return "running"
        if self.started_at is not None:
            return "preparation"
        if self.requested_execution_at is not None:
            return "scheduled"
        return "created"

    @property
    def skipped_execution(self) -> bool:
        return self.finished_at is not None and self.executed_at is None

    @property
    def has_missing_data(self) -> bool:
        return (
            self.finished_at is not None
            and self.executed_at is not None
            and super().has_missing_data
        )

    @property
    def had_errors(self) -> bool:
        return (
            self.max_exit_code > 0
            or self.scheduler_error is not None
            or self.skipped_execution
            or self.has_missing_data
            or len(self.missing_observers) > 0
        )

    async def update_time_start(
        self, time_start: datetime | None = None, *, force: bool = False
    ) -> None:
        if not force and self.experiment.time_start is not None:  # do not force if already there
            return
        if time_start is None:
            if not isinstance(self.result_paths, dict) or len(self.result_paths) == 0:
                log.error("Could not update Experiment.time_start from files")
                return
            with CoreReader(next(iter(self.result_paths.values()))) as shp_rd:
                time_start = shp_rd.get_time_start()
        xp = self.experiment.model_dump()
        xp["time_start"] = time_start
        self.experiment = Experiment(**xp)
        await self.save_changes()

    @property
    def summary(self) -> str:
        def as_iso(ts: datetime | None) -> str:
            return ts.isoformat(sep=" ")[:19] + " (UTC)" if ts is not None else "-"

        return (
            "\nSummary:\n"
            f"- id = {self.id}\n"
            f"- duration = {self.experiment.duration} hms\n"
            f"- scheduled @ {as_iso(self.started_at)}\n"
            f"- executed  @ {as_iso(self.executed_at)}\n"
            f"- finished  @ {as_iso(self.finished_at)}\n"
        )


class ExperimentStats(Document):
    """This will get updated sporadically throughout the life-time of WebExperiment.
    This will at least get created before WebExp gets deleted.
    """

    id: UUID

    owner: EmailStr | None = None

    created_at: datetime | None = None
    started_at: datetime | None = None
    executed_at: datetime | None = None
    finished_at: datetime | None = None

    deleted_at: datetime | None = None

    state: str | None = None
    duration: timedelta | None = None
    result_size: int = 0

    had_errors: bool = False
    skipped_execution: bool | None = None
    has_missing_data: bool = False
    max_exit_code: int | None = None
    scheduler_error: str | None = None
    missing_observers: list[str] | None = None

    # TODO: if these statistics stay, consider adding
    #      - used eenvs &
    #      - targets / node-count / used MCUs?
    #      - which tracers are used?
    #      - to get a feeling what is desired

    class Settings:  # allows using .save_changes()
        use_state_management = True
        state_management_save_previous = True
        validate_on_save = True

    @classmethod
    async def derive_from(cls, wxp: WebExperiment) -> Self:
        data = cls(id=wxp.id)
        data.update_common_fields(wxp)
        await data.save()
        return data

    def update_common_fields(self, wxp: WebExperiment) -> None:
        if not isinstance(wxp.owner, User):
            raise TypeError("User of Experiment could not be verified")
        self.owner = wxp.owner.email
        # timestamps
        self.created_at = wxp.created_at
        self.started_at = wxp.started_at
        self.executed_at = wxp.executed_at
        self.finished_at = wxp.finished_at
        # states
        self.state = wxp.state
        self.duration = wxp.experiment.duration
        self.result_size = wxp.result_size
        # errors
        self.had_errors = wxp.had_errors
        self.skipped_execution = wxp.skipped_execution
        self.has_missing_data = wxp.has_missing_data
        self.max_exit_code = wxp.max_exit_code
        self.scheduler_error = wxp.scheduler_error
        self.missing_observers = wxp.missing_observers

    @classmethod
    async def update_with(
        cls,
        wxp: WebExperiment,
        *,
        to_be_deleted: bool = False,
    ) -> Self:

        data: Self = await cls.find_one(cls.id == wxp.id)
        if data is None:
            data = await cls.derive_from(wxp)
        else:
            data.update_common_fields(wxp)

        if to_be_deleted:
            data.deleted_at = datetime.now(tz=local_tz())
        await data.save_changes()
        return data

    @classmethod
    async def get_by_id(cls, experiment_id: UUID) -> None | Self:
        return await cls.find_one(
            cls.id == experiment_id,
        )

    @classmethod
    async def get_all_states(cls, user: User | None = None) -> dict[UUID, str]:
        if user is None:
            data = await cls.all(lazy_parse=True).to_list()
        else:
            data = await cls.find(
                cls.owner == user.email,
                lazy_parse=True,
            ).to_list()
        return {date.id: date.state for date in data}
