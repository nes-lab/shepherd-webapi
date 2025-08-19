from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from shepherd_core import local_now

from shepherd_server.api_user.models import User
from shepherd_server.api_user.utils_misc import verify_password_hash

from .models import AccessToken
from .utils import create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> AccessToken:
    _user = await User.by_email(form_data.username)
    if not _user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if not verify_password_hash(form_data.password, _user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if _user.email_confirmed_at is None:
        raise HTTPException(status_code=401, detail="Email is not yet verified")
    if _user.disabled:
        raise HTTPException(status_code=401, detail="Account is disabled")
    _user.last_active_at = local_now()
    await _user.save_changes()
    return create_access_token(_user.email)
