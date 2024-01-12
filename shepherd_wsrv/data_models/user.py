"""User models."""

from datetime import datetime
from hashlib import sha512, sha3_512
from typing import Annotated, Any, Optional

from beanie import Document, Indexed
from pydantic import BaseModel, EmailStr

from shepherd_wsrv.config import CFG


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

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    def __str__(self) -> str:
        return self.email

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
    async def by_email(cls, email: str) -> Optional["User"]:
        """Get a user by email."""
        return await cls.find_one(cls.email == email)

    def update_email(self, new_email: str) -> None:
        """Update email logging and replace."""
        # Add any pre-checks here
        self.email = new_email
