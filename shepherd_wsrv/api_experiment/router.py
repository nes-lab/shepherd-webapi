from datetime import datetime
from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Response
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
    if experiment.time_start is not None:
        raise HTTPException(
            400,
            "time_start must be None,"
            "the testbed will pick the start time after the experiment is scheduled.",
        )

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
    if web_experiment is None:
        raise HTTPException(404, "Not Found")
    if web_experiment.owner.email != user.email:
        raise HTTPException(403, "Forbidden")
    return web_experiment.experiment


@router.post("/{experiment_id}/schedule")
async def schedule_experiment(
    experiment_id: str,
    user: Annotated[User, Depends(current_active_user)],
):
    web_experiment = await WebExperiment.get_by_id(UUID4(experiment_id))
    if web_experiment is None:
        raise HTTPException(404, "Not Found")
    if web_experiment.owner.email != user.email:
        raise HTTPException(403, "Forbidden")

    # TODO it would be possible to schedule the same experiment multiple times...

    web_experiment.requested_execution_at = datetime.now()
    await web_experiment.save()

    return Response(status_code=204)


@router.get("/{experiment_id}/state")
async def get_experiment_state(
    experiment_id: str,
    user: Annotated[User, Depends(current_active_user)],
):
    web_experiment = await WebExperiment.get_by_id(UUID4(experiment_id))
    if web_experiment is None:
        raise HTTPException(404, "Not Found")

    # TODO route privacy should be modeled canonically
    if web_experiment.owner.email != user.email:
        raise HTTPException(403, "Forbidden")

    if web_experiment.finished_at is not None:
        return "finished"

    if web_experiment.started_at is not None:
        return "running"

    if web_experiment.requested_execution_at is not None:
        return "scheduled"

    return "created"


@router.get("/{experiment_id}/download")
async def download(
    experiment_id: str,
    user: Annotated[User, Depends(current_active_user)],
):
    web_experiment = await WebExperiment.get_by_id(UUID4(experiment_id))
    if web_experiment is None:
        raise HTTPException(404, "Not Found")

    # TODO route privacy should be modeled canonically
    if web_experiment.owner.email != user.email:
        raise HTTPException(403, "Forbidden")

    if web_experiment.finished_at is None:
        raise HTTPException(400, "Experiment not yet finished")

    output_paths = web_experiment.testbed_tasks.get_output_paths()
    return list(output_paths.keys())

