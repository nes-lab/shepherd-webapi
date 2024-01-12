from fastapi import APIRouter, Depends

from shepherd_wsrv.routes.auth import get_current_active_user
from shepherd_wsrv.data_models import User

router = APIRouter(prefix="/users", tags=["User"])


@router.get("/")
async def user_info(user: User = Depends(get_current_active_user)):
    return user
