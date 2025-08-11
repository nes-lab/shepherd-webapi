from datetime import datetime

from beanie import Document
from pydantic import BaseModel
from pydantic import HttpUrl


class SchedulerStatus(BaseModel):
    activated: datetime | None = None
    busy: bool = False
    dry_run: bool = False
    last_update: datetime | None = None
    observer_count: int = 0
    observers_online: list[str] = []
    observers_offline: list[str] = []


class RedirectStatus(BaseModel):
    activated: datetime | None = None
    url: HttpUrl | None = None


class ApiStatus(BaseModel):
    activated: datetime | None = None


class TestbedStatus(BaseModel):
    restrictions: list[str] | None = None

    timestamp_timezone: str = "UTC"

    webapi: ApiStatus = ApiStatus()
    scheduler: SchedulerStatus = SchedulerStatus()
    redirect: RedirectStatus = RedirectStatus()

    server_version: str | None = None
    herd_version: str | None = None
    core_version: str | None = None


class TestbedDB(TestbedStatus, Document):
    class Settings:  # allows using .save_changes()
        use_state_management = True
        state_management_save_previous = True
        validate_on_save = True

    @classmethod
    async def get_one(cls) -> "TestbedDB":
        wtb = await cls.find_one()
        if wtb is None:
            wtb = cls()
            await wtb.save()
        return wtb
