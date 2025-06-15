from datetime import datetime

from beanie import Document


class Scheduler(Document):
    active: bool = False
    dry_run: bool = False
    last_seen: datetime | None = None
    observer_count: int = 0
    observers: list[str] | None = None

    @classmethod
    async def get_one(cls) -> "Scheduler":
        sdl = await cls.find_one()
        return cls() if sdl is None else sdl
