import asyncio
import copy
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from pathlib import PurePosixPath
from tempfile import TemporaryDirectory

import numpy as np
from beanie import Link
from fabric import Result
from pydantic import UUID4
from shepherd_core import Writer as CoreWriter
from shepherd_core import local_now
from shepherd_core import local_tz
from shepherd_core.data_models.task import TestbedTasks
from shepherd_core.data_models.testbed import Testbed
from shepherd_herd.herd import Herd

from .api_experiment.models import WebExperiment
from .api_testbed.models_status import TestbedDB
from .api_user.models import User
from .api_user.utils_mail import mail_engine
from .config import config
from .instance_db import db_available
from .instance_db import db_client
from .logger import log


def replies2str(replies: Mapping[str, Result]) -> str:
    """Log output-results of shell commands."""
    # sort dict by key first
    replies = dict(sorted(replies.items()))
    string = ""
    for hostname, reply in replies.items():
        if len(reply.stdout) > 0:
            string += f"\n************** {hostname} - stdout **************"
            string += reply.stdout
        if len(reply.stderr) > 0:
            string += f"\n~~~~~~~~~~~~~~ {hostname} - stderr ~~~~~~~~~~~~~~"
            string += reply.stderr
        string += f"Exit-code of {hostname} = {reply.exited}"
    return string


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
        paths_result: dict[str, Path] = {}
        paths_content: dict[str, Path] = {}

        if temp_path is not None:
            await asyncio.sleep(10)  # mocked length
            # create mocked files
            paths_task = testbed_tasks.get_output_paths()
            paths_content["all"] = temp_path / experiment.folder_name()
            for name, path_task in paths_task.items():
                paths_result[name] = temp_path / experiment.folder_name() / path_task.name

                with CoreWriter(paths_result[name]) as writer:
                    writer.store_hostname(name)
                    writer.append_iv_data_si(
                        timestamp=local_now().timestamp(),
                        voltage=np.zeros(10_000),
                        current=np.zeros(10_000),
                    )
        else:
            # force other sheep-instances to end
            herd.run_cmd(sudo=True, cmd="pkill shepherd-sheep")
            # modified herd.run_task(testbed_tasks, attach=True, quiet=True)
            remote_path = PurePosixPath("/etc/shepherd/config_for_herd.yaml")
            herd.put_task(testbed_tasks, remote_path)
            command = f"shepherd-sheep --verbose run {remote_path.as_posix()}"
            replies = herd.run_cmd(sudo=True, cmd=command)
            exit_code = max([0] + [abs(reply.exited) for reply in replies.values()])

            if exit_code > 0:
                log.error("Running Experiment failed on at least one Observer")
                error_log = replies2str(replies)
                await mail_engine().send_error_log_email(
                    config.contact["email"],
                    web_exp.id,
                    experiment.name,
                    error_log,
                )
                if (
                    isinstance(web_exp.owner, Link | User)
                    and config.contact["email"] != web_exp.owner.email
                ):
                    await mail_engine().send_error_log_email(
                        web_exp.owner.email,
                        web_exp.id,
                        experiment.name,
                        error_log,
                    )

            await asyncio.sleep(20)  # finish IO, precaution
            # paths to direct files
            paths_result = testbed_tasks.get_output_paths()
            # TODO: hardcoded bending of observer to server path-structure
            #       from sheep-path: /var/shepherd/experiments/xp_name
            #       to server-path:  /var/shepherd/experiments/sheep_name/xp_name
            for observer in copy.deepcopy(paths_result):
                path_obs = paths_result[observer].absolute()
                if not path_obs.is_relative_to("/var/shepherd/experiments"):
                    log.error("Path outside of experiment-location? %s", path_obs.as_posix())
                    paths_result.pop(observer)
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
                    paths_result.pop(observer)
                    continue
                paths_result[observer] = path_srv
            # paths to directories with all content like firmware, h5-results, ...
            paths_content = testbed_tasks.get_output_paths()
            for observer in copy.deepcopy(paths_content):
                path_obs = paths_content[observer].absolute().parent
                path_rel = path_obs.relative_to("/var/shepherd/experiments")
                path_srv = Path("/var/shepherd/experiments") / observer / path_rel
                try:
                    path_srv_exists = path_srv.exists()
                except PermissionError:
                    path_srv_exists = False
                if not path_srv_exists:
                    paths_content.pop(observer)
                    continue
                paths_content[observer] = path_srv

        log.info("finished task execution")

        # mark job as done in database
        _size = 0
        for path in paths_result.values():
            if path.exists() and path.is_file():
                _size += path.stat().st_size
            else:
                log.warning(f"file '{path}' does not exist after the experiment")
        # Reload XP to avoid race-condition / working on old data
        web_exp = await WebExperiment.get_by_id(xp_id)
        if web_exp is None:
            log.warning("Dataset of Experiment not found after running it (deleted?)")
            return
        if len(paths_result) > 0:
            web_exp.result_paths = paths_result
        if len(paths_content) > 0:
            web_exp.content_paths = paths_content
        web_exp.result_size = _size
        web_exp.finished_at = datetime.now(tz=local_tz())
        await web_exp.update_time_start()
        await web_exp.save()

        # send out Mail if user wants it
        if not isinstance(web_exp.owner, Link | User):
            return
        all_done = await WebExperiment.has_scheduled_by_user(web_exp.owner)
        if experiment.email_results or all_done:
            await mail_engine().send_experiment_finished_email(
                web_exp.owner.email, web_exp.id, experiment.name, all_done=all_done
            )


async def update_status(
    inventory: Path | None = None, *, active: bool = False, dry_run: bool = False
) -> None:
    _client = await db_client()
    tb_ = await TestbedDB.get_one()
    tb_.scheduler.active = active
    tb_.scheduler.dry_run = dry_run
    tb_.scheduler.last_update = local_now()
    if dry_run:
        tb_.observer_count = 0
        tb_.observers = None
    else:
        with Herd(inventory=inventory) as herd:
            tb_.observer_count = len(herd.group)
            tb_.observers = [herd.hostnames[cnx.host] for cnx in herd.group]
    await tb_.save()


async def scheduler(inventory: Path | None = None, *, dry_run: bool = False) -> None:
    _client = await db_client()

    # allow running dry in temp-folder
    with TemporaryDirectory() as temp_dir:
        temp_path: Path | None = None
        if dry_run:
            log.warning("Dry run mode - not executing tasks!")
            temp_path = Path(temp_dir)
            log.debug("Temp path: %s", temp_path.resolve())

        # TODO: how to make sure there is only one scheduler? Singleton
        log.info("Checking experiment scheduling FIFO")
        await WebExperiment.reset_stuck_items()

        while True:
            await update_status(inventory=inventory, active=True, dry_run=dry_run)
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

    try:
        asyncio.run(scheduler(inventory, dry_run=dry_run))
    except SystemExit:
        asyncio.run(update_status(inventory, dry_run=dry_run))


if __name__ == "__main__":
    run()
