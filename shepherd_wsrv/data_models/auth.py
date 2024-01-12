"""Auth response models."""

from datetime import timedelta
from hashlib import sha3_512

from pydantic import BaseModel

from shepherd_wsrv.config import CFG


class AccessToken(BaseModel):
    """Access token details."""

    access_token: str
    access_token_expires: timedelta = timedelta(minutes=15)


class RefreshToken(AccessToken):
    """Access and refresh token details."""

    refresh_token: str
    refresh_token_expires: timedelta = timedelta(days=30)


def calculate_hash(pw: str) -> str:
    """automatically salts & hashes a password"""
    if not CFG.auth_salt:
        raise EnvironmentError("[AUTH-HASH] No auth salt configured")
    return sha3_512(pw.encode('UTF-8') + CFG.auth_salt.encode("UTF-8")).hexdigest()
