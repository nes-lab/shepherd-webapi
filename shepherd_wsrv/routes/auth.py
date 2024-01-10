from http.client import HTTPException

from fastapi import Form, APIRouter
from fastapi.security import OAuth2PasswordBearer
from shepherd_core import tb_client

from shepherd_wsrv.data_models.product import Product
from shepherd_core.data_models import Wrapper
from shepherd_core.data_models import content as shp_cnt
from shepherd_core.data_models import testbed as shp_tb


router = APIRouter(prefix="/auth", tags=["Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


@router.post("/login")
async def login(username: str = Form(), password: str = Form()):
    return {"username": username}


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
