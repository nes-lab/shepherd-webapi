import asyncio
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from pydantic import UUID4
from shepherd_core import Writer as CoreWriter
from shepherd_core import local_now
from shepherd_core import local_tz
from shepherd_core.data_models.task import TestbedTasks
from shepherd_core.data_models.testbed import Testbed
from shepherd_herd.herd import Herd

from .api_experiment.models import WebExperiment
from .config import config
from .instance_db import db_available
from .instance_db import db_client
from .logger import log


async def run_web_experiment(
    xp_id: UUID4, inventory: Path | None = None, temp_path: Path | None = None
) -> None:
    # mark as started
    web_exp = await WebExperiment.get_by_id(xp_id)
    if web_exp is None:
        log.warning("Dataset of Experiment not found before running it (deleted?)")
        return
    web_exp.started_at = datetime.now(tz=local_tz())
    await web_exp.save()

    experiment = web_exp.experiment

    testbed = Testbed(name=config.testbed_name)
    testbed_tasks = TestbedTasks.from_xp(experiment, testbed)

    with Herd(inventory=inventory) as herd:
        log.info("starting testbed tasks through herd-tool")
        paths_herd: dict[str, Path] = {}

        if temp_path is not None:
            await asyncio.sleep(10)  # mocked length
            # create mocked files
            paths_task = testbed_tasks.get_output_paths()
            for name, path_task in paths_task.items():
                paths_herd[name] = temp_path / experiment.folder_name() / path_task.name
                with CoreWriter(paths_herd[name]) as writer:
                    writer.store_hostname(name)
                    writer.append_iv_data_si(
                        timestamp=local_now().timestamp(),
                        voltage=np.zeros(10_000),
                        current=np.zeros(10_000),
                    )
        else:
            exit_code = herd.run_task(testbed_tasks, attach=True, quiet=True)
            if exit_code > 0:
                log.warning("Run had errors - could have been failed.")
            await asyncio.sleep(20)  # finish IO, precaution
            paths_herd = testbed_tasks.get_output_paths()
            # TODO: hardcoded bending of observer to server path-structure
            #       from sheep-path: /var/shepherd/experiments/xp_name
            #       to server-path:  /var/shepherd/experiments/sheep_name/xp_name
            for observer in paths_herd:
                path_obs = paths_herd[observer].absolute()
                if not path_obs.is_relative_to("/var/shepherd/experiments"):
                    log.error("Path outside of experiment-location? %s", path_obs.as_posix())
                    paths_herd.pop(observer)
                    continue
                try:
                    path_obs_exists = path_obs.exists()
                except PermissionError:
                    path_obs_exists = False
                if path_obs_exists:
                    log.warning("Observer-Path should not exist on server! %s", path_obs.as_posix())
                path_rel = path_obs.relative_to("/var/shepherd/experiments")
                path_srv = Path("/var/shepherd/experiments") / observer / path_rel
                try:
                    path_srv_exists = path_srv.exists()
                except PermissionError:
                    log.error("Permission-Error on Server-Path -> will skip!")
                    path_srv_exists = False
                if not path_srv_exists:
                    log.error("Server-Path must exist on server! %s", path_srv.as_posix())
                    paths_herd.pop(observer)
                    continue
                paths_herd[observer] = path_srv

        log.info("finished task execution")
        # TODO: email on error - extract logs & mail?

        # mark job as done in database
        _size = 0
        for path in paths_herd.values():
            if path.exists() and path.is_file():
                _size += path.stat().st_size
            else:
                log.warning(f"file '{path}' does not exist after the experiment")
        # Reload XP to avoid race-condition / working on old data
        web_exp = await WebExperiment.get_by_id(xp_id)
        if web_exp is None:
            log.warning("Dataset of Experiment not found after running it (deleted?)")
            return
        web_exp.result_paths = paths_herd
        web_exp.result_size = _size
        web_exp.finished_at = datetime.now(tz=local_tz())
        await web_exp.update_time_start()
        await web_exp.save()
        # TODO: send out Email here (if wanted)


async def scheduler(inventory: Path | None = None, *, dry_run: bool = False) -> None:
    _client = await db_client()

    # allow running dry in temp-folder
    stack = ExitStack()
    _temp_dir = TemporaryDirectory()
    stack.enter_context(_temp_dir)
    temp_path: Path | None = None
    if dry_run:
        log.warning("Dry run mode - not executing tasks!")
        temp_path = Path(_temp_dir.name)
        log.debug("Temp path: %s", temp_path.resolve())

    # TODO: how to make sure there is only one scheduler? Singleton
    log.info("Checking experiment scheduling FIFO")
    await WebExperiment.reset_stuck_items()

    while True:
        next_experiment = await WebExperiment.get_next_scheduling()
        if next_experiment is None:
            log.debug("... waiting 10 s")
            await asyncio.sleep(10)
            continue

        log.debug("Scheduling experiment '%s'", next_experiment.experiment.name)
        await run_web_experiment(next_experiment.id, inventory=inventory, temp_path=temp_path)


def run(inventory: Path | None = None, *, dry_run: bool = False) -> None:
    if not db_available(timeout=5):
        log.error("No connection to database! Will exit scheduler now.")
        return

    # loop = asyncio.new_event_loop()
    # loop.run_until_complete(scheduler(inventory, dry_run=dry_run))
    asyncio.run(scheduler(inventory, dry_run=dry_run))


if __name__ == "__main__":
    run()
