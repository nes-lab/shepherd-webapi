from datetime import datetime
from datetime import timedelta
from datetime import timezone

from fastapi import HTTPException
from fastapi import status
from jose import JWTError
from jose import jwt

from shepherd_wsrv.api_auth.models import AccessToken
from shepherd_wsrv.config import CFG


def create_access_token(username: str, expires_delta: timedelta = timedelta(days=1)) -> AccessToken:
    to_encode = {"sub": username}
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return AccessToken(
        access_token=jwt.encode(to_encode, CFG.secret_key, algorithm="HS256"),
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
        payload = jwt.decode(token, CFG.secret_key, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as xpt:
        raise credentials_exception from xpt
    return username
