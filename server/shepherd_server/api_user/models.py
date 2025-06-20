"""User models."""

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from enum import Enum
from typing import Annotated
from typing import Any
from typing import Optional

from beanie import Document
from beanie import Indexed
from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field
from pydantic import PositiveInt
from pydantic import StringConstraints
from pydantic import computed_field
from shepherd_core import local_now
from shepherd_core import local_tz

from shepherd_server.config import config

PasswordStr = Annotated[str, StringConstraints(min_length=10, max_length=64, pattern=r"^[ -~]+$")]
# ⤷ Regex = All Printable ASCII-Characters with Space


class UserRole(str, Enum):
    """Options for roles."""

    user = "user"
    elevated = "elevated"
    admin = "admin"
    # TODO: add group-admin, elevated user (VIP privileges like faster path for scheduler)


class UserRegistration(BaseModel):
    """User data needed for registration."""

    email: EmailStr
    password: PasswordStr
    token: str


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
    storage_available: PositiveInt | None = None
    """updated when user asks for its info.
    fill level should be computed_field/property, but created circular import"""

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

    @computed_field
    @property
    def quota_duration(self) -> timedelta:
        _custom = self.custom_quota_active and (self.custom_quota_duration is not None)
        return self.custom_quota_duration if _custom else config.quota_default_duration

    @computed_field
    @property
    def quota_storage(self) -> PositiveInt:
        _custom = self.custom_quota_active and (self.custom_quota_storage is not None)
        return self.custom_quota_storage if _custom else config.quota_default_storage


class UserOut(UserQuota, UserUpdate):
    """User fields returned to the client."""

    disabled: bool = True
    email: Annotated[EmailStr, Indexed(unique=True)]
    group: str = ""  # TODO: will come later
    role: UserRole = UserRole.user


class User(Document, UserOut):
    """User DB representation."""

    # id: UUID4 = Field(default_factory=uuid4)

    password_hash: str

    created_at: datetime = Field(default_factory=local_now)
    last_active_at: datetime = Field(default_factory=local_now)

    email_confirmed_at: datetime | None = None
    group_confirmed_at: datetime | None = None
    token_verification: str | None = None
    token_pw_reset: str | None = None

    class Settings:  # allows using .save_changes()
        use_state_management = True
        state_management_save_previous = True

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    def __str__(self) -> str:
        return str(self.email)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, User) and self.email == other.email

    def __hash__(self) -> int:  # sync with __eq__
        return hash(self.email)

    @property
    def created(self) -> datetime | None:
        """Datetime user was created from ID."""
        # TODO: deprecated - use .created_at field - not used ATM?
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
