from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from shepherd_core.data_models import Experiment

from shepherd_wsrv.api_experiment.models import ExperimentDB
from shepherd_wsrv.api_user.models import User
from shepherd_wsrv.api_user.utils_misc import current_active_user

router = APIRouter(prefix="/experiment", tags=["Experiment"])
# TODO: should we fuse the decorator directly to the model-methods?


@router.get("", response_model=list[Experiment])
async def get_all_experiments(user: Annotated[User, Depends(current_active_user)]):
    return await ExperimentDB.get_by_user(user=user)


@router.post("")
async def add_experiment(xp: ExperimentDB, user: Annotated[User, Depends(current_active_user)]):
    xp.owner_id = user.id
    await ExperimentDB.insert_one(xp)
    result = True
    # should users see ID or have control over it?
    # TODO: add to DB, return ID and success.msg
    return {"successful": result, "id": xp.id}


@router.patch("/{xp_id}/activate")
async def activate_experiment(xp_id: int, user: Annotated[User, Depends(current_active_user)]):
    result = await ExperimentDB.activate(xp_id, user)
    return {"successful": result}


@router.get("/{xp_id}", response_model=None | Experiment)
async def get_experiment(xp_id: int, user: Annotated[User, Depends(current_active_user)]):
    return await ExperimentDB.get_by_id(xp_id, user)


@router.delete("/{xp_id}")
async def delete_experiment(xp_id: int, user: Annotated[User, Depends(current_active_user)]):
    result = await ExperimentDB.set_to_delete(xp_id, user)
    return {"successful": result}
