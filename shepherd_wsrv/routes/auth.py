from hashlib import sha512

from fastapi import Form, APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from shepherd_wsrv.config import CFG
from shepherd_wsrv.data_models import User


router = APIRouter(prefix="/auth", tags=["Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


async def decode_user_token(token: str = Depends(oauth2_scheme)) -> User:
    return await User.by_email(token)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    # TODO: db[token], token should be username == email in our case
    user = User(email="mr@sister.ord", password="thisIsSecure", group=token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    _user = await decode_user_token(form_data.username)
    if not _user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    _hash = User.calculate_hash(form_data.password)
    if not _user.password == _hash:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    if _user.email_confirmed_at is None:
        raise HTTPException(status_code=400, detail="Email is not yet verified")
    return {"access_token": _user.username, "token_type": "bearer"}


@router.get("/session_key")
async def read_session_key():
    # TODO
    return {"value": b"this_will_be_a_asym_pubkey"}


@router.get("/user")
async def read_userdata(token: str):
    # TODO
    return {
        "name": "Klaus",
        "group": "TU Dresden",
        "email": "test@best.com",
        "token": token,
    }
