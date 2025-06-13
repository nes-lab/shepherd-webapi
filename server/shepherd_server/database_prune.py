from shepherd_core import local_now

from .api_experiment.models import WebExperiment
from .api_user.models import User
from .config import config
from .instance_db import db_client
from .logger import log


async def prune_db(*, dry_run: bool = True) -> int:
    """Clean up database.

    - delete old users and their content
    - trim users to be below quota
    - delete old experiments
    """
    _client = await db_client()
    users_old = await User.find(
        User.last_active_at <= local_now() - config.age_max_user,
        fetch_links=True,
    ).to_list()
    size_xp = await WebExperiment.prune(users_old, dry_run=dry_run)
    size_total = sum([size_xp])

    if dry_run:
        log.info("Pruning Users (inactive, over-quota) could free: %d MiB", size_total / (2**20))
    else:
        for user in users_old:
            log.debug(" -> deleting user %s", user.email)
            await user.delete()
        log.info("Pruning Users (inactive, over-quota) freed: %d MiB", size_total / (2**20))
    return size_total
