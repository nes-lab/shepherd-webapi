"""Auth response models."""

from datetime import timedelta

from pydantic import BaseModel


class AccessToken(BaseModel):
    """Access token details."""

    access_token: str
    token_type: str
    access_token_expires: timedelta = timedelta(minutes=15)


class RefreshToken(AccessToken):
    """Access and refresh token details."""

    # TODO: not used ATM

    refresh_token: str
    token_type: str
    refresh_token_expires: timedelta = timedelta(days=30)
