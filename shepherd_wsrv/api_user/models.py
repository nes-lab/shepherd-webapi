"""User models."""

from datetime import datetime
from typing import Annotated
from typing import Any
from typing import Optional
from typing_extensions import Self

from beanie import Document
from beanie import Indexed
from pydantic import BaseModel
from pydantic import EmailStr


class UserAuth(BaseModel):
    """User register and login auth."""

    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Updatable user fields."""

    email: EmailStr | None = None

    # User information
    first_name: str | None = None
    last_name: str | None = None


class UserOut(UserUpdate):
    """User fields returned to the client."""

    disabled: bool = True
    email: Annotated[str, Indexed(EmailStr, unique=True)]
    group: str = ""  # TODO: will come later
    role: str | None = None  # TODO: enum? user, group_admin, sys_admin


class User(Document, UserOut):
    """User DB representation."""

    password: str
    email_confirmed_at: datetime | None = None
    group_confirmed_at: datetime | None = None
    token_verification: str | None = None
    token_pw_reset: str | None = None

    def __repr__(self: Self) -> str:
        return f"<User {self.email}>"

    def __str__(self: Self) -> str:
        return self.email

    def __eq__(self: Self, other: object) -> bool:
        if isinstance(other, User):
            return self.email == other.email
        return False

    @property
    def created(self: Self) -> datetime | None:
        """Datetime user was created from ID."""
        return self.id.generation_time if self.id else None

    @property
    def subject(self: Self) -> dict[str, Any]:
        """JWT subject fields."""
        return {"username": self.email}

    @classmethod
    async def by_email(cls: Self, email: str | None) -> Optional["User"]:
        """Get a user by email."""
        if email is None:
            return None
        return await cls.find_one(cls.email == email)

    @classmethod
    async def by_verification_token(cls: Self, token: str) -> Optional["User"]:
        return await cls.find_one(cls.token_verification == token)

    @classmethod
    async def by_reset_token(cls: Self, token: str) -> Optional["User"]:
        return await cls.find_one(cls.token_pw_reset == token)

    def update_email(self: Self, new_email: str) -> None:
        """Update email logging and replace."""
        # Add any pre-checks here
        self.email = new_email
