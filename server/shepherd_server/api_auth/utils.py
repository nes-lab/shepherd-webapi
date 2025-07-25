from datetime import datetime
from datetime import timedelta

from fastapi import HTTPException
from fastapi import status
from jose import JWTError
from jose import jwt
from shepherd_core import local_tz

from shepherd_server.config import config

from .models import AccessToken


def create_access_token(username: str, expires_delta: timedelta = timedelta(days=1)) -> AccessToken:
    to_encode = {"sub": username}
    expire = datetime.now(tz=local_tz()) + expires_delta
    to_encode.update({"exp": expire})
    return AccessToken(
        access_token=jwt.encode(to_encode, config.secret_key, algorithm="HS256"),
        token_type="bearer",  # noqa: S106, not a secret
        access_token_expires=expires_delta,
    )


def decode_access_token(token: str) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.secret_key, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as xpt:
        raise credentials_exception from xpt
    return username
