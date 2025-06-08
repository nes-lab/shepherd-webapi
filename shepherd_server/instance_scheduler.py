import asyncio
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from shepherd_core import Writer as CoreWriter
from shepherd_core import local_tz
from shepherd_core.data_models.task import TestbedTasks
from shepherd_core.data_models.testbed import Testbed
from shepherd_herd.herd import Herd

from shepherd_server.instance_db import db_available
from shepherd_server.instance_db import db_client

from .api_experiment.models import WebExperiment
from .logger import log


async def run_web_experiment(
    web_experiment: WebExperiment, inventory: Path | None = None, temp_path: Path | None = None
) -> None:
    # mark as started
    web_experiment.started_at = datetime.now(tz=local_tz())
    await web_experiment.save()

    experiment = web_experiment.experiment

    # TODO: too much hardcode
    testbed = Testbed(name="matthias-office")
    testbed_tasks = TestbedTasks.from_xp(experiment, testbed)

    # Sadly, we must materialize the tasks here, although this is redundant information.
    # Yet it is necessary later to compute the download paths.
    web_experiment.testbed_tasks = testbed_tasks
    # TODO: tasks don't have to be saved, just store paths and their size

    herd = Herd(inventory=inventory)
    with herd:
        log.info("starting testbed tasks through herd-tool")
        paths_herd: dict[str, Path] = {}

        if temp_path is not None:
            # create mocked files
            paths_task = testbed_tasks.get_output_paths()
            for name, path_task in paths_task.items():
                paths_herd[name] = temp_path / path_task.name
                with CoreWriter(paths_herd[name]) as writer:
                    writer.store_hostname(name)
        else:
            herd.run_task(testbed_tasks, attach=True)
            await asyncio.sleep(20)  # finish IO, precaution
            # TODO: paths must probably be bend from sheep to server structure
            #       from sheep-path: /var/shepherd/experiments/xp_name
            #       to server-path:  /var/shepherd/experiments/sheep_name/xp_name
            paths_herd = testbed_tasks.get_output_paths()

        log.info("finished task execution")

        # mark job as done in database
        _size = 0
        for path in paths_herd.values():
            if path.exists() and path.is_file():
                _size += path.stat().st_size
            else:
                log.warning(f"file '{path}' does not exist after the experiment")
        web_experiment.result_paths = paths_herd
        web_experiment.result_size = _size
        web_experiment.finished_at = datetime.now(tz=local_tz())
        # TODO: update time_start in real experiment, once it finishes
        await web_experiment.save()


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

    log.info("Checking experiment scheduling FIFO")

    while True:
        next_experiment = await WebExperiment.get_next_scheduling()
        if next_experiment is None:
            log.debug("... waiting 10 s")
            await asyncio.sleep(10)
            continue

        log.debug("Scheduling experiment '%s'", next_experiment.experiment.name)
        await run_web_experiment(next_experiment, inventory=inventory, temp_path=temp_path)


def run(inventory: Path | None = None, *, dry_run: bool = False) -> None:
    if not db_available(timeout=5):
        log.error("No connection to database! Will exit scheduler now.")
        return

    loop = asyncio.new_event_loop()
    loop.run_until_complete(scheduler(inventory, dry_run=dry_run))


if __name__ == "__main__":
    run()
