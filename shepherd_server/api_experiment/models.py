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
from shepherd_core.data_models.task import TestbedTasks

from shepherd_server.api_user.models import User
from shepherd_server.config import CFG
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

    testbed_tasks: TestbedTasks | None = None  # TODO: not used ATM
    result_paths: dict[str, Path] | None = None
    result_size: int = 0

    @classmethod
    async def get_by_id(cls, experiment_id: str) -> "None | WebExperiment":
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
            .sort(  # TODO: this should be fine without list-encaps
                [
                    (WebExperiment.created_at, pymongo.ASCENDING),
                ],
            )
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
                cls.requested_execution_at != None,  # noqa: E711 beanie cannot handle 'is not None' expressions
                cls.started_at == None,  # noqa: E711 beanie cannot handle 'is not None' expressions
            )
            .sort(
                [  # TODO: this should be fine without list-encaps
                    (WebExperiment.requested_execution_at, pymongo.ASCENDING),
                ],
            )
            .limit(1)
            .to_list()
        )
        if len(next_experiments) > 0:
            return next_experiments[0]
        return None

    @classmethod
    async def prune(cls, *, dry_run: bool = True) -> int:
        # TODO: remove items with missing link to user (zombies)
        size_total = 0
        experiments_old = await cls.find(
            cls.created_at <= local_now() - CFG.age_max_experiment,
            fetch_links=True,
        ).to_list()
        size_total = sum(xp.result_size for xp in experiments_old)
        if dry_run:
            log.info("Pruning old experiments could free: %d MiB", size_total / (2**20))
        else:
            for xp in experiments_old:
                await xp.delete_content()
                await xp.delete()
            log.info("Pruning old experiments freed: %d MiB", size_total / (2**20))
        return size_total

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
        if not isinstance(self.result_paths, dict):
            log.error("Could not update Experiment.time_start")
            return
        with CoreReader(next(self.result_paths.values())) as shp_rd:
            time_start = shp_rd.get_time_start()
        xp = self.experiment.model_dump()
        xp["time_start"] = time_start
        self.xp = Experiment(**xp)
