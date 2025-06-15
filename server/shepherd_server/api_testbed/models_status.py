from datetime import datetime

from beanie import Document
from pydantic import BaseModel


class SchedulerStatus(BaseModel):
    active: bool = False
    dry_run: bool = False
    last_seen: datetime | None = None


class RedirectStatus(BaseModel):
    active: bool = False
    last_seen: datetime | None = None


class TestbedStatus(BaseModel):
    observer_count: int = 0
    observers: list[str] | None = None

    timestamp_timezone: str = "UTC"

    scheduler: SchedulerStatus = SchedulerStatus()
    redirect: RedirectStatus = RedirectStatus()


class TestbedDB(TestbedStatus, Document):
    @classmethod
    async def get_one(cls) -> "TestbedDB":
        wtb = await cls.find_one()
        return cls() if wtb is None else wtb
