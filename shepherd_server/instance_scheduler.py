import asyncio
from datetime import datetime

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from shepherd_core import local_tz
from shepherd_core.data_models.task import TestbedTasks
from shepherd_core.data_models.testbed import Testbed
from shepherd_herd.herd import Herd

from shepherd_server.api_experiment.models import WebExperiment
from shepherd_server.api_user.models import User
from shepherd_server.logger import log


async def run_web_experiment(web_experiment: WebExperiment, *, dry_run: bool = False) -> None:
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

    # TODO: move inventory file to environment variable
    herd = Herd(
        inventory="/home/matthias/dev/shepherd/repo/software/shepherd-webapi/herd.yml",
    )
    with herd:
        log.info("starting testbed tasks through herd tool")

        if not dry_run:
            herd.run_task(testbed_tasks, attach=True)

        log.info("finished task execution")

        # mark job as done in database
        web_experiment.finished_at = datetime.now(tz=local_tz())
        await web_experiment.save()


async def scheduler() -> None:
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    await init_beanie(database=client.shp, document_models=[User, WebExperiment])
    log.info("Checking experiment scheduling FIFO")

    while True:
        next_experiment = await WebExperiment.get_next_scheduling()
        if next_experiment is None:
            log.debug("No experiment scheduled, waiting 10 s")
            await asyncio.sleep(10)
            continue

        log.debug("Scheduling experiment")
        await run_web_experiment(next_experiment)


def run() -> None:
    loop = asyncio.new_event_loop()
    loop.run_until_complete(scheduler())


if __name__ == "__main__":
    run()
