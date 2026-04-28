from hashlib import sha3_512
from typing import Annotated

from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import OAuth2PasswordBearer
from passlib.hash import pbkdf2_sha512

from shepherd_server.api_auth.utils import decode_access_token
from shepherd_server.config import server_config

from .models import User
from .models import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")  # Url = full route


def calculate_password_hash(pw: str) -> str:
    """Automatically salts & hashes a password"""
    if not server_config.auth_salt:
        raise OSError("[AUTH-HASH] No auth salt configured")
    return pbkdf2_sha512.using(salt=server_config.auth_salt).hash(pw)


def verify_password_hash(pw_plain: str, pw_hash: str) -> bool:
    if not server_config.auth_salt:
        raise OSError("[AUTH-HASH] No auth salt configured")
    return pbkdf2_sha512.using(salt=server_config.auth_salt).verify(pw_plain, pw_hash)


def calculate_hash(text: str) -> str:
    if not server_config.auth_salt:
        raise OSError("[AUTH-HASH] No auth salt configured")
    return sha3_512(server_config.auth_salt + text.encode("UTF-8")).hexdigest()


async def query_user(token: Annotated[str | None, Depends(oauth2_scheme)]) -> User | None:
    if not token:
        return None
    email = decode_access_token(token)
    return await User.by_email(email)


async def current_user(token: Annotated[str | None, Depends(oauth2_scheme)]) -> User:
    # allows basic functionality: login, get account info, delete account
    _user = await query_user(token)
    if not _user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _user


async def active_user(user: Annotated[User, Depends(current_user)]) -> User:
    if user.disabled:
        raise HTTPException(status_code=403, detail="Account is currently deactivated")
    if user.email_confirmed_at is None:
        raise HTTPException(status_code=401, detail="Email is not yet verified")
    return user


async def active_elevated_user(user: Annotated[User, Depends(active_user)]) -> User:
    if user.role not in (UserRole.admin, UserRole.elevated):
        raise HTTPException(status_code=403, detail="Forbidden")
    return user


async def active_admin_user(user: Annotated[User, Depends(active_user)]) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    return User
