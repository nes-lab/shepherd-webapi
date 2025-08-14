import asyncio

from shepherd_server import WebExperiment
from shepherd_server.instance_db import db_available
from shepherd_server.instance_db import db_client
from shepherd_server.logger import log


async def db_delete_old_experiments() -> None:
    _client = await db_client()

    await WebExperiment.find_one(WebExperiment.scheduler_error == [None, None]).delete()


def run() -> None:
    if not db_available(timeout=5):
        log.error("No connection to database! Will exit scheduler now.")
        return
    asyncio.run(db_delete_old_experiments())


if __name__ == "__main__":
    run()
