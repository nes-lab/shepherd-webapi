"""Specific Database migration

Bugfix:
- finished stats that are not present in WebExperiments are deleted
- add deletíon date & change state (hardcoded)

"""

import asyncio

from shepherd_core import local_now
from shepherd_server.api_experiments.models import ExperimentStats
from shepherd_server.api_experiments.models import WebExperiment
from shepherd_server.instance_db import db_available
from shepherd_server.instance_db import db_client
from shepherd_server.instance_fixtures import prepare_fixture_client
from shepherd_server.logger import log


async def repair_db() -> None:
    await db_client

    if not db_available(timeout=2):
        return

    st_states = await ExperimentStats.get_all_states()
    xp_states = await WebExperiment.get_all_states()

    for uid, state in st_states.items():
        xp_stat = await ExperimentStats.get_by_id(uid)
        if xp_stat is None:
            raise ValueError("This should not have happened.")

        if xp_stat.state == "finished" and xp_stat.id not in xp_states:
            log.info("Fixing XP-Statistic %s - wrong state '%s'", uid, state)
            xp_stat.state = "deleted"
            await xp_stat.save_changes()

        if xp_stat.state == "deleted" and xp_stat.deleted_at is None:
            log.info("Fixing XP-Statistic %s - missing deletion-timestamp ", uid)
            xp_stat.deleted_at = local_now()
            await xp_stat.save_changes()


if __name__ == "__main__":
    if not db_available(timeout=5):
        raise ConnectionError("No connection to database! Will exit scheduler now.")
    prepare_fixture_client()
    asyncio.run(repair_db())
