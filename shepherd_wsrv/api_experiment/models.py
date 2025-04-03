from datetime import datetime
from uuid import uuid4

import pymongo
from beanie import Document
from beanie import Link
from pydantic import UUID4
from pydantic import Field
from shepherd_core.data_models import Experiment

from shepherd_wsrv.api_user.models import User


class WebExperiment(Document):
    id: UUID4 = Field(default_factory=uuid4)
    owner: Link[User] | None = None
    experiment: Experiment
    scheduled_at: datetime | None = None

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
                cls.scheduled_at != None,  # noqa: E711 beanie cannot handle 'is not None' expressions
            )
            .sort(
                [
                    (WebExperiment.scheduled_at, pymongo.ASCENDING),
                ],
            )
            .limit(1)
            .to_list()
        )
        if len(next_experiments) > 0:
            return next_experiments[0]
        return None
