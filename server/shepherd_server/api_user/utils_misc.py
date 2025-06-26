from hashlib import sha3_512
from typing import Annotated

from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import OAuth2PasswordBearer
from passlib.hash import pbkdf2_sha512

from shepherd_server.api_auth.utils import decode_access_token
from shepherd_server.config import config

from .models import User
from .models import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")  # Url = full route


def calculate_password_hash(pw: str) -> str:
    """Automatically salts & hashes a password"""
    if not config.auth_salt:
        raise OSError("[AUTH-HASH] No auth salt configured")
    return pbkdf2_sha512.using(salt=config.auth_salt).hash(pw)


def verify_password_hash(pw_plain: str, pw_hash: str) -> bool:
    if not config.auth_salt:
        raise OSError("[AUTH-HASH] No auth salt configured")
    return pbkdf2_sha512.using(salt=config.auth_salt).verify(pw_plain, pw_hash)


def calculate_hash(text: str) -> str:
    if not config.auth_salt:
        raise OSError("[AUTH-HASH] No auth salt configured")
    return sha3_512(config.auth_salt + text.encode("UTF-8")).hexdigest()


async def query_user(token: Annotated[str | None, Depends(oauth2_scheme)]) -> User | None:
    if not token:
        return None
    email = decode_access_token(token)
    return await User.by_email(email)


async def current_user(token: Annotated[str | None, Depends(oauth2_scheme)]) -> User:
    _user = await query_user(token)
    if not _user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _user


async def current_active_user(user: Annotated[User, Depends(current_user)]) -> User:
    if user.disabled:
        raise HTTPException(status_code=403, detail="Deactivated user")
    return user


async def active_user_is_elevated(user: Annotated[User, Depends(current_user)]) -> None:
    if user.role not in (UserRole.admin, UserRole.elevated):
        raise HTTPException(status_code=403, detail="Forbidden")


async def active_user_is_admin(user: Annotated[User, Depends(current_user)]) -> None:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Forbidden")
