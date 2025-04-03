from time import sleep

from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI
from motor.core import AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient
from shepherd_core import local_now

from shepherd_wsrv.api_experiment.models import WebExperiment
from shepherd_wsrv.api_user.models import User
from shepherd_wsrv.api_user.utils_misc import calculate_password_hash
from shepherd_core.data_models.testbed import Testbed
from shepherd_core.data_models.task import TestbedTasks

import asyncio

from shepherd_herd.herd import Herd
from pathlib import Path


async def run_web_experiment(web_experiment: WebExperiment):

    experiment = web_experiment.experiment

    tb = Testbed(name="matthias-office")
    tb_tasks = TestbedTasks.from_xp(experiment, tb)
    print("converted to testbed task")
    tb_tasks.to_file("experiment_generic_var1_tbt.yaml")

    # TODO move inventory file to environment variable
    herd = Herd(
        inventory="/home/matthias/dev/shepherd/repo/software/shepherd-webservice/herd.yml",
    )
    with herd:
        remote_path = Path("/etc/shepherd/config.yaml")
        print("trying to put task")
        herd.put_task(tb_tasks, remote_path)
        print("put task")
        exit_code = herd.start_measurement()
        print("started measurement")
        print(exit_code)

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    await init_beanie(database=client.shp, document_models=[User, WebExperiment])

    while True:
        # TODO convert all prints to proper logs
        print('Checking experiment scheduling FIFO')

        next_experiment = await WebExperiment.get_next_scheduling()
        if next_experiment is None:
            print('No experiment scheduled')
            print('Waiting 5 sec...')
            await asyncio.sleep(5)
            continue

        print('scheduling experiment')
        next_experiment.scheduled_at = None
        await next_experiment.save()

        await run_web_experiment(next_experiment)

if __name__ ==  '__main__':
    loop = asyncio.new_event_loop   ()
    loop.run_until_complete(main())

