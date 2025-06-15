from datetime import datetime
from pathlib import Path
from uuid import UUID
from uuid import uuid4

import pymongo
from beanie import Document
from beanie import Link
from pydantic import Field
from shepherd_core import Reader as CoreReader
from shepherd_core import local_now
from shepherd_core.data_models import Experiment

from shepherd_server.api_user.models import User
from shepherd_server.config import config
from shepherd_server.logger import log


class WebExperiment(Document):
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

    result_paths: dict[str, Path] | None = None
    result_size: int = 0

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
    async def get_next_scheduling(cls) -> "None | WebExperiment":
        """
        Finds the WebExperiment with the oldest scheduling_at datetime,
        that has not been executed yet (status less than active).
        """
        next_experiments = (
            await cls.find(
                cls.requested_execution_at != None,  # noqa: E711 beanie cannot handle 'is not None'
                cls.started_at == None,  # noqa: E711
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
        ).to_list()
        for _xp in stuck_xps:
            log.info("Resetting experiment: %s", _xp.id)
            _xp.started_at = None
            await _xp.save()

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
        if self.finished_at is not None:
            if self.result_paths is not None:
                return "finished"
            return "failed"
        if self.started_at is not None:
            return "running"
        if self.requested_execution_at is not None:
            return "scheduled"
        return "created"

    async def delete_content(self) -> None:
        # TODO: just overwrite default delete-method?
        if isinstance(self.result_paths, dict):
            # TODO: removing files for now - should switch to paths
            #       (leftover firmware and meta-data)
            for result_file in self.result_paths.values():
                if result_file.exists() and result_file.is_file():
                    result_file.unlink()
            self.result_paths = None

    async def update_time_start(self) -> None:
        if not isinstance(self.result_paths, dict) or len(self.result_paths) == 0:
            log.error("Could not update Experiment.time_start from files")
            return
        with CoreReader(next(iter(self.result_paths.values()))) as shp_rd:
            time_start = shp_rd.get_time_start()
        xp = self.experiment.model_dump()
        xp["time_start"] = time_start
        self.experiment = Experiment(**xp)
