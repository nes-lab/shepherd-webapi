from datetime import datetime
from uuid import UUID
from uuid import uuid4

import pymongo
from beanie import Document
from beanie import Link
from pydantic import Field
from shepherd_core.data_models import Experiment
from shepherd_core.data_models.task import TestbedTasks

from shepherd_server.api_user.models import User


class WebExperiment(Document):
    id: UUID = Field(default_factory=uuid4)
    owner: Link[User] | None = None
    experiment: Experiment

    # None, if the experiment should not be executed.
    # Set by the API to current wall-clock time when the user requests the experiment
    # to be executed.
    # This is NOT the time when the experiment should be run!
    requested_execution_at: datetime | None = None

    # None, when the experiment is not yet executing on the testbed.
    # Set to current wall-clock time when the web runner picks to experiment and
    # starts execution on the testbed.
    started_at: datetime | None = None

    # None, when the experiment is not yet finished (still executing or not yet started).
    # Set to current wall-clock time by the web runner when the testbed finished execution.
    finished_at: datetime | None = None

    # TODO: convert to paths?
    testbed_tasks: TestbedTasks | None = None

    @classmethod
    async def get_by_id(cls, experiment_id: str) -> "None | WebExperiment":
        return await cls.find_one(
            cls.id == experiment_id,
            fetch_links=True,
        )

    @classmethod
    async def get_by_user(cls, user: User) -> list["WebExperiment"]:
        return await cls.find(
            cls.owner.email == user.email,
            fetch_links=True,
        ).to_list()

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
                [
                    (WebExperiment.requested_execution_at, pymongo.ASCENDING),
                ],
            )
            .limit(1)
            .to_list()
        )
        if len(next_experiments) > 0:
            return next_experiments[0]
        return None
