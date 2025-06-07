"""User models."""

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Annotated
from typing import Any
from typing import Optional

from beanie import Document
from beanie import Indexed
from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import PositiveInt
from pydantic import StringConstraints
from shepherd_core import local_tz

from shepherd_server.config import CFG

PasswordStr = Annotated[str, StringConstraints(min_length=10, max_length=64, pattern=r"^[ -~]+$")]
# ⤷ Regex = All Printable ASCII-Characters with Space


class UserAuth(BaseModel):
    """User register and login auth."""

    email: EmailStr
    password: PasswordStr


class UserUpdate(BaseModel):
    """Updatable user fields."""

    email: EmailStr | None = None

    # User information
    first_name: str | None = None
    last_name: str | None = None


class UserQuota(BaseModel):
    custom_quota_expire_date: datetime | None = None
    custom_quota_duration: timedelta | None = None
    custom_quota_storage: PositiveInt | None = None

    @property
    def custom_quota_active(self) -> bool:
        """
        note: model is transmitted via fastapi / json and
              therefore lost timezone (normalized to UTC)
        """
        if self.custom_quota_expire_date is None:
            return False
        if self.custom_quota_expire_date.tzinfo is None:
            return self.custom_quota_expire_date.replace(tzinfo=timezone.utc) >= datetime.now(
                tz=local_tz()
            )
        return self.custom_quota_expire_date >= datetime.now(tz=local_tz())

    @property
    def quota_duration(self) -> timedelta:
        _custom = self.custom_quota_active and (self.custom_quota_duration is not None)
        return self.custom_quota_duration if _custom else CFG.quota_default_duration

    @property
    def quota_storage(self) -> int:
        _custom = self.custom_quota_active and (self.custom_quota_storage is not None)
        return self.custom_quota_storage if _custom else CFG.quota_default_storage


class UserOut(UserUpdate, UserQuota):
    """User fields returned to the client."""

    disabled: bool = True
    email: Annotated[EmailStr, Indexed(unique=True)]
    group: str = ""  # TODO: will come later
    role: str | None = None  # TODO: enum? user, group_admin, sys_admin


class User(Document, UserOut):
    """User DB representation."""

    # id: UUID4 = Field(default_factory=uuid4)

    password_hash: str
    email_confirmed_at: datetime | None = None
    group_confirmed_at: datetime | None = None
    token_verification: str | None = None
    token_pw_reset: str | None = None

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    def __str__(self) -> str:
        return str(self.email)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, User):
            return self.email == other.email
        return False

    @property
    def created(self) -> datetime | None:
        """Datetime user was created from ID."""
        return self.id.generation_time if self.id else None

    @property
    def subject(self) -> dict[str, Any]:
        """JWT subject fields."""
        return {"username": self.email}

    @classmethod
    async def by_email(cls, email: EmailStr | None) -> Optional["User"]:
        """Get a user by email."""
        if email is None:
            return None
        return await cls.find_one(cls.email == email)

    @classmethod
    async def by_verification_token(cls, token: str) -> Optional["User"]:
        return await cls.find_one(cls.token_verification == token)

    @classmethod
    async def by_reset_token(cls, token: str) -> Optional["User"]:
        return await cls.find_one(cls.token_pw_reset == token)

    def update_email(self, new_email: EmailStr) -> None:
        """Update email logging and replace."""
        # Add any pre-checks here
        self.email = new_email
