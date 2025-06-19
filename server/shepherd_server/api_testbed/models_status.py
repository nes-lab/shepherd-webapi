from datetime import datetime

from beanie import Document
from pydantic import BaseModel


class SchedulerStatus(BaseModel):
    active: bool = False
    busy: bool = False
    dry_run: bool = False
    last_update: datetime | None = None
    observer_count: int = 0
    observers: list[str] | None = None


class RedirectStatus(BaseModel):
    active: bool = False
    last_update: datetime | None = None


class ApiStatus(BaseModel):
    activated: datetime | None = None


class TestbedStatus(BaseModel):
    restrictions: list[str] | None = None

    timestamp_timezone: str = "UTC"

    webapi: ApiStatus = ApiStatus()
    scheduler: SchedulerStatus = SchedulerStatus()
    redirect: RedirectStatus = RedirectStatus()


class TestbedDB(TestbedStatus, Document):
    class Settings:  # allows using .save_changes()
        use_state_management = True
        state_management_save_previous = True

    @classmethod
    async def get_one(cls) -> "TestbedDB":
        wtb = await cls.find_one()
        if wtb is None:
            wtb = cls()
            wtb.save_changes()
        return wtb
