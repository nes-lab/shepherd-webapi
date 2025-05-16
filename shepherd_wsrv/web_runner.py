import asyncio
from datetime import datetime

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from shepherd_core import local_tz
from shepherd_core.data_models.task import TestbedTasks
from shepherd_core.data_models.testbed import Testbed
from shepherd_herd.herd import Herd

from shepherd_wsrv.api_experiment.models import WebExperiment
from shepherd_wsrv.api_user.models import User


async def run_web_experiment(web_experiment: WebExperiment, *, dry_run: bool = False) -> None:
    # mark as started
    web_experiment.started_at = datetime.now(tz=local_tz())
    await web_experiment.save()

    experiment = web_experiment.experiment

    # TODO:
    testbed = Testbed(name="matthias-office")
    testbed_tasks = TestbedTasks.from_xp(experiment, testbed)

    # Sadly, we must materialize the tasks here, although this is redundant information.
    # Yet it is necessary later to compute the download paths.
    web_experiment.testbed_tasks = testbed_tasks

    # TODO: move inventory file to environment variable
    herd = Herd(
        inventory="/home/matthias/dev/shepherd/repo/software/shepherd-webservice/herd.yml",
    )
    with herd:
        print("starting testbed tasks through herd tool")

        if not dry_run:
            herd.run_task(testbed_tasks, attach=True)
        print("finished task execution")

        # mark job as done in database
        web_experiment.finished_at = datetime.now(tz=local_tz())
        await web_experiment.save()


async def main() -> None:
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    await init_beanie(database=client.shp, document_models=[User, WebExperiment])

    while True:
        # TODO: convert all prints to proper logs
        print("Checking experiment scheduling FIFO")

        next_experiment = await WebExperiment.get_next_scheduling()
        if next_experiment is None:
            print("No experiment scheduled")
            print("Waiting 5 sec...")
            await asyncio.sleep(5)
            continue

        print("scheduling experiment")
        await run_web_experiment(next_experiment)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
