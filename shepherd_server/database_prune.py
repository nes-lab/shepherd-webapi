from shepherd_core import local_now

from shepherd_server.api_experiment.models import WebExperiment
from shepherd_server.api_user.models import User
from shepherd_server.config import CFG
from shepherd_server.logger import log


async def prune_users(*, dry_run: bool = True) -> int:
    """Delete old users and their content.

    This will also trim users to be below quota again.
    """
    users_old = await User.find(
        User.last_active_at <= local_now() - CFG.age_max_user,
        fetch_links=True,
    ).to_list()
    xps_2_prune = []
    for user in users_old:
        xps_2_prune += await WebExperiment.get_by_user(user)

    users_all = await User.find_all().to_list()
    xp_date_limit = local_now() - CFG.age_min_experiment
    for user in users_all:
        xps_user = await WebExperiment.get_by_user(user)  # already sorted by age
        storage_user = WebExperiment.get_storage(user)
        for xp in xps_user:
            if xp.created_at >= xp_date_limit:
                break
            if storage_user >= user.quota_storage:
                xps_2_prune.append(xp)
                storage_user -= xp.result_size

    xps_2_prune = set(xps_2_prune)
    size_total = sum(xp.result_size for xp in xps_2_prune)

    if dry_run:
        log.info("Pruning Users (inactive, over-quota) could free: %d MiB", size_total / (2**20))
    else:
        for xp in xps_2_prune:
            await xp.delete_content()
            await xp.delete()
        for user in users_old:
            await user.delete()
        log.info("Pruning Users (inactive, over-quota) freed: %d MiB", size_total / (2**20))
    return size_total


async def prune_experiments(*, dry_run: bool = True) -> int:
    return await WebExperiment.prune(dry_run=dry_run)
