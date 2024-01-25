import asyncio
from typing import Optional

from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer

from .models import User
from hashlib import sha3_512
from passlib.hash import pbkdf2_sha512

from shepherd_wsrv.config import CFG
from ..api_auth.utils import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")  # Url = full route


def calculate_password_hash(pw: str) -> str:
    """automatically salts & hashes a password"""
    if not CFG.auth_salt:
        raise EnvironmentError("[AUTH-HASH] No auth salt configured")
    return pbkdf2_sha512.using(salt=CFG.auth_salt).hash(pw)


def verify_password_hash(pw_plain: str, pw_hash: str) -> bool:
    if not CFG.auth_salt:
        raise EnvironmentError("[AUTH-HASH] No auth salt configured")
    return pbkdf2_sha512.using(salt=CFG.auth_salt).verify(pw_plain, pw_hash)


def calculate_hash(text: str) -> str:
    if not CFG.auth_salt:
        raise EnvironmentError("[AUTH-HASH] No auth salt configured")
    return sha3_512(text.encode("UTF-8") + CFG.auth_salt).hexdigest()


async def query_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[User]:
    if not token:
        return None
    email = decode_access_token(token)
    return await User.by_email(email)


async def current_user(token: Optional[str] = Depends(oauth2_scheme)) -> User:
    _user = await query_user(token)
    if not _user:
        await asyncio.sleep(1)  # rate limit
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _user


async def current_active_user(user: User = Depends(current_user)) -> User:
    if user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user






