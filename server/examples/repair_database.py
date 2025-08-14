import asyncio

from server.shepherd_server.instance_db import db_available, db_client
from server.shepherd_server.logger import log
from server import WebExperiment

async def db_delete_old_experiments() -> None:
    _client = await db_client()

    xp_wrong = await WebExperiment.find(WebExperiment.scheduler_error == [None, None])
    xp_wrong.delete()




def run() -> None:
    if not db_available(timeout=5):
        log.error("No connection to database! Will exit scheduler now.")
        return
    asyncio.run(db_delete_old_experiments())


if __name__ == "__main__":
    run()