from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from pydantic import UUID4
from shepherd_core.data_models import Experiment

from shepherd_wsrv.api_experiment.models import WebExperiment
from shepherd_wsrv.api_user.models import User
from shepherd_wsrv.api_user.utils_misc import current_active_user

router = APIRouter(prefix="/experiment", tags=["Experiment"])


@router.post("/")
async def create_experiment(
    experiment: Experiment,
    user: Annotated[User, Depends(current_active_user)],
):
    web_experiment = WebExperiment(
        experiment=experiment,
        owner=user,
    )
    await web_experiment.save()
    return web_experiment.id


@router.get("/")
async def list_experiments(
    user: Annotated[User, Depends(current_active_user)],
):
    web_experiments = await WebExperiment.get_by_user(user)
    experiments = {}
    for web_experiment in web_experiments:
        experiments[web_experiment.id] = web_experiment.experiment

    return experiments


@router.get("/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    user: Annotated[User, Depends(current_active_user)],
):
    web_experiment = await WebExperiment.get_by_id(UUID4(experiment_id))
    if web_experiment.owner.email != user.email:
        raise HTTPException(403, "Forbidden")
    return web_experiment.experiment
