from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Response
from pydantic import UUID4
from shepherd_core import local_tz
from shepherd_core.data_models import Experiment
from starlette.responses import FileResponse

from shepherd_server.api_user.models import User
from shepherd_server.api_user.utils_misc import current_active_user

from .models import WebExperiment

router = APIRouter(prefix="/experiment", tags=["Experiment"])


@router.post("/")
async def create_experiment(
    experiment: Experiment,
    user: Annotated[User, Depends(current_active_user)],
) -> UUID:
    if experiment.time_start is not None:
        raise HTTPException(
            400,
            "xp.time_start must be None,"
            "the FIFO-scheduler will pick the start time after the experiment is scheduled.",
        )
    if (experiment.duration is None) or (experiment.duration > user.quota_duration):
        raise HTTPException(
            400, f"xp.duration must be set to value <= {user.quota_duration} s (user-quota)"
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
) -> dict[UUID, Experiment]:
    web_experiments = await WebExperiment.get_by_user(user)
    experiments: dict[UUID, Experiment] = {}
    for web_experiment in web_experiments:
        experiments[web_experiment.id] = web_experiment.experiment

    return experiments


@router.get("/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    user: Annotated[User, Depends(current_active_user)],
) -> Experiment:
    web_experiment = await WebExperiment.get_by_id(UUID4(experiment_id))
    if web_experiment is None:
        raise HTTPException(404, "Not Found")
    if web_experiment.owner.email != user.email:
        raise HTTPException(403, "Forbidden")
        # TODO: maybe also emit 404 to leak less data - but since UUID is used its min hit-rate
    return web_experiment.experiment


@router.delete("/{experiment_id}")
async def delete_experiment(
    experiment_id: str,
    user: Annotated[User, Depends(current_active_user)],
) -> Response:
    web_experiment = await WebExperiment.get_by_id(UUID4(experiment_id))
    if web_experiment is None:
        raise HTTPException(404, "Not Found")
    if web_experiment.owner.email != user.email:
        raise HTTPException(403, "Forbidden")
    if web_experiment.started_at is not None and web_experiment.finished_at is None:
        # TODO: possible race-condition
        raise HTTPException(403, "Experiment is running - cannot delete")
    if isinstance(web_experiment.result_paths, dict):
        # TODO: removing files for now - should switch to paths (leftover firmware and meta-data)
        for path in web_experiment.result_paths.values():
            if path.exists() and path.is_file():
                path.unlink()
    await web_experiment.delete()
    return Response(status_code=204)


@router.post("/{experiment_id}/schedule")
async def schedule_experiment(
    experiment_id: str,
    user: Annotated[User, Depends(current_active_user)],
) -> Response:
    web_experiment = await WebExperiment.get_by_id(UUID4(experiment_id))
    if web_experiment is None:
        raise HTTPException(404, "Not Found")
    if web_experiment.owner.email != user.email:
        raise HTTPException(403, "Forbidden")
    if web_experiment.requested_execution_at is not None:
        raise HTTPException(400, "Experiment already scheduled")
    _storage = await web_experiment.get_storage(user)
    if _storage > user.quota_storage:
        _size_GiB = _storage / (1024**3)
        _quota_GiB = user.quota_storage / (1024**3)
        raise HTTPException(
            400,
            f"Quota on storage was exceeded ({_size_GiB:.3f} > {_quota_GiB:.3f} GiB). "
            "Delete old experiments first to continue.",
        )

    web_experiment.requested_execution_at = datetime.now(tz=local_tz())
    await web_experiment.save()

    return Response(status_code=204)


@router.get("/{experiment_id}/state")
async def get_experiment_state(
    experiment_id: str,
    user: Annotated[User, Depends(current_active_user)],
) -> str:
    web_experiment = await WebExperiment.get_by_id(UUID4(experiment_id))
    if web_experiment is None:
        raise HTTPException(404, "Not Found")

    # TODO: route privacy should be modeled canonically
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
) -> list[str]:
    web_experiment = await WebExperiment.get_by_id(UUID4(experiment_id))
    if web_experiment is None:
        raise HTTPException(404, "Not Found")

    # TODO: route privacy should be modeled canonically
    if web_experiment.owner.email != user.email:
        raise HTTPException(403, "Forbidden")

    if web_experiment.finished_at is None or web_experiment.result_paths is None:
        raise HTTPException(400, "Experiment not yet finished")

    return list(web_experiment.result_paths.keys())


@router.get("/{experiment_id}/download/{observer}")
async def download_sheep_file(
    experiment_id: str,
    observer: str,
    user: Annotated[User, Depends(current_active_user)],
) -> FileResponse:
    web_experiment = await WebExperiment.get_by_id(UUID4(experiment_id))
    if web_experiment is None:
        raise HTTPException(404, "Not Found")

    # TODO: route privacy should be modeled canonically
    if web_experiment.owner.email != user.email:
        raise HTTPException(403, "Forbidden")

    if observer not in web_experiment.result_paths:
        raise HTTPException(404, "Observer not contained in resulting list of the experiment.")

    output_path = web_experiment.result_paths[observer]

    if not output_path.exists() or not output_path.is_file():
        raise HTTPException(404, "File not found on server (but it should exist).")

    return FileResponse(output_path.as_posix())
