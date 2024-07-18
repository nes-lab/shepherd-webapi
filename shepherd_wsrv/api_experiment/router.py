from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from pydantic import UUID4

from shepherd_wsrv.api_experiment.models import WebExperiment
from shepherd_wsrv.api_user.models import User
from shepherd_wsrv.api_user.utils_misc import current_active_user

router = APIRouter(prefix="/experiment", tags=["Experiment"])


@router.post("/")
async def create_experiment(
    web_experiment: WebExperiment,
    user: Annotated[User, Depends(current_active_user)],
):
    web_experiment.owner = user
    await web_experiment.save()
    return web_experiment


@router.get("/")
async def list_experiments(
    user: Annotated[User, Depends(current_active_user)],
):
    return await WebExperiment.get_by_user(user)


@router.get("/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    user: Annotated[User, Depends(current_active_user)],
):
    experiment = await WebExperiment.get_by_id(UUID4(experiment_id))
    if experiment.owner.email != user.email:
        raise HTTPException(403, "Forbidden")
    return experiment
