import copy
import shutil
import subprocess
from datetime import datetime
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
from pydantic import Field
from shepherd_core import Reader as CoreReader
from shepherd_core import local_now
from shepherd_core.data_models import Experiment

from shepherd_server.api_user.models import User
from shepherd_server.api_user.models import UserRole
from shepherd_server.config import config
from shepherd_server.logger import log


def obtain_access_permissions(path: Path) -> None:
    ret = subprocess.run(  # noqa: S603
        ["/usr/bin/sudo", "/usr/bin/chmod", "a+rw", "-R", path.as_posix()],
        capture_output=False,
        timeout=20,
        check=False,
        stderr=None,
        stdout=None,
    ).returncode
    if ret != 0:
        log.warning("Changing permission denied for %s", path)


class ResultData(BaseModel):
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
        for path in self.result_paths.values():
            if path.exists() and path.is_file():
                _size += path.stat().st_size
            else:
                log.warning(f"file '{path}' does not exist after the experiment")
        self.result_size = _size
        await self.save_changes()

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
        if len(self.result_paths) > 0:
            self.content_paths = {key: path.parent for key, path in self.result_paths.items()}
            await self.update_size()
        else:
            log.warning("Skipped adding empty content path list")
            self.content_paths = None
            self.result_paths = None
        await self.save_changes()

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
        await self.save_changes()


class ReplyData(BaseModel):
    exited: int
    stdout: str
    stderr: str


class ErrorData(BaseModel):
    # status & error - log
    observers_online: set[str] | None = None
    observers_offline: set[str] | None = None

    observers_output: dict[str, ReplyData] | None = None

    scheduler_error: str | None = None

    def get_terminal_output(self, *, only_faulty: bool = False) -> list[UploadFile]:
        """Log output-results of shell commands."""
        files = []
        if self.observers_output is None:
            return files
        # sort dict by key first
        replies = dict(sorted(self.observers_output.items()))
        for hostname, reply in replies.items():
            if only_faulty and abs(reply.exited) == 0:
                continue
            string = ""
            if len(reply.stdout) > 0:
                string += f"\n************** {hostname} - stdout **************\n"
                string += reply.stdout
            if len(reply.stderr) > 0:
                string += f"\n~~~~~~~~~~~~~~ {hostname} - stderr ~~~~~~~~~~~~~~\n"
                string += reply.stderr
            string += f"\nExit-code of {hostname} = {reply.exited}\n"
            files.append(UploadFile(filename="error.log", file=StringIO(string)))
        return files

    @property
    def max_exit_code(self) -> int:
        if self.observers_output is None:
            return 0
        return max([0] + [abs(reply.exited) for reply in self.observers_output.values()])

    @property
    def had_errors(self) -> bool:
        return (
            (self.max_exit_code > 0)
            or self.scheduler_error is not None
            or len(self.observers_offline) > 0
        )


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
    None, when the experiment is not yet executing on the testbed.
    Set to current wall-clock time when the web runner picks to experiment and
    starts execution on the testbed.
    """

    finished_at: datetime | None = None
    """
    None, when the experiment is not yet finished (still executing or not yet started).
    Set to current wall-clock time by the web runner when the testbed finished execution.
    """

    class Settings:  # allows using .save_changes()
        use_state_management = True
        state_management_save_previous = True

    @classmethod
    async def get_by_id(cls, experiment_id: UUID) -> "None | WebExperiment":
        return await cls.find_one(
            cls.id == experiment_id,
            fetch_links=True,
        )

    @classmethod
    async def get_by_user(cls, user: User) -> list["WebExperiment"]:
        return await (
            cls.find(
                cls.owner.email == user.email,
                fetch_links=True,
            )
            .sort((WebExperiment.created_at, pymongo.ASCENDING))
            .to_list()
        )

    @classmethod
    async def get_storage(cls, user: User) -> int:
        _xps = await cls.get_by_user(user)
        return sum(_xp.result_size for _xp in _xps)

    @classmethod
    async def get_next_scheduling(cls, *, only_elevated: bool = False) -> "None | WebExperiment":
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
            .sort((WebExperiment.requested_execution_at, pymongo.ASCENDING))
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
            cls.scheduler_error == None,  # noqa: E711
        ).to_list()
        for _xp in stuck_xps:
            log.info("Resetting experiment: %s", _xp.id)
            _xp.started_at = None
            await _xp.save_changes()

    @classmethod
    async def prune(cls, users: list[User] | None = None, *, dry_run: bool = True) -> int:
        # TODO: find xp with missing link to user (zombies)
        xps_2_prune = []

        # fetch experiments by user
        if users is not None:
            for user in users:
                xps_2_prune += await cls.get_by_user(user)

        # get oldest XP of users over quota
        users_all = await User.find_all().to_list()
        xp_date_limit = local_now() - config.age_min_experiment
        for user in users_all:
            xps_user = await cls.get_by_user(user)  # already sorted by age
            storage_user = cls.get_storage(user)
            for xp in xps_user:
                if xp.created_at >= xp_date_limit:
                    break
                if storage_user >= user.quota_storage:
                    xps_2_prune.append(xp)
                    storage_user -= xp.result_size

        # get xp exceeding max age
        xps_2_prune += await cls.find(
            cls.created_at <= local_now() - config.age_max_experiment,
            fetch_links=True,
        ).to_list()

        # calculate size of experiments
        xps_2_prune = set(xps_2_prune)
        size_total = sum(xp.result_size for xp in xps_2_prune)

        if dry_run:
            log.info("Pruning old experiments could free: %d MiB", size_total / (2**20))
        else:
            for xp in xps_2_prune:
                log.debug(" -> deleting experiment %s", xp.name)
                await xp.delete_content()
                await xp.delete()
            log.info("Pruning old experiments freed: %d MiB", size_total / (2**20))
        return size_total

    @property
    def state(self) -> str:
        if self.scheduler_error is not None:
            return "failed"
        if self.finished_at is not None:
            if self.result_paths is not None:
                return "finished"
            return "failed"
        if self.started_at is not None:
            return "running"
        if self.requested_execution_at is not None:
            return "scheduled"
        return "created"

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
