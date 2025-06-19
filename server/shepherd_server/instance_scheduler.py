import asyncio
import copy
import subprocess
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
            string += f"\n************** {hostname} - stdout **************\n"
            string += reply.stdout
        if len(reply.stderr) > 0:
            string += f"\n~~~~~~~~~~~~~~ {hostname} - stderr ~~~~~~~~~~~~~~\n"
            string += reply.stderr
        string += f"\nExit-code of {hostname} = {reply.exited}\n"
    return string


def obtain_access_permissions(path: Path) -> None:
    ret = subprocess.run(  # noqa: S603
        ["/usr/bin/sudo", "/usr/bin/chmod", "a+rw", "-R", path.as_posix()],
        timeout=20,
        check=False,
    ).returncode
    if ret != 0:
        log.warning("Changing permission denied for %s", path)


async def run_web_experiment(
    xp_id: UUID4, temp_path: Path, inventory: Path | None = None, *, dry_run: bool = False
) -> None:
    # mark as started
    web_exp = await WebExperiment.get_by_id(xp_id)
    if web_exp is None:
        log.warning("Dataset of Experiment not found before running it (deleted?)")
        return
    web_exp.started_at = datetime.now(tz=local_tz())
    await web_exp.save_changes()

    experiment = web_exp.experiment

    testbed = Testbed(name=config.testbed_name)
    testbed_tasks = TestbedTasks.from_xp(experiment, testbed)
    # TODO: set custom time if possible herd.start_delay_s = 5 * 60, herd.find_consensus_time()

    log.info("starting testbed tasks through herd-tool")
    paths_result: dict[str, Path] = {}
    paths_content: dict[str, Path] = {}

    if dry_run:
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
        with Herd(inventory=inventory) as herd:
            # force other sheep-instances to end
            herd.run_cmd(sudo=True, cmd="pkill shepherd-sheep")
            # below is a modified herd.run_task(testbed_tasks, attach=True, quiet=True)
            remote_path = PurePosixPath("/etc/shepherd/config_for_herd.pickle")
            herd.put_task(task=testbed_tasks, remote_path=remote_path)
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

        # paths to directories with all content like firmware, h5-results, ...
        paths_content = testbed_tasks.get_output_paths()
        for observer in copy.deepcopy(paths_content):
            path_obs = paths_content[observer].absolute().parent
            path_rel = path_obs.relative_to("/var/shepherd/experiments")
            path_srv = Path("/var/shepherd/experiments") / observer / path_rel
            obtain_access_permissions(path_srv)
            try:
                path_srv_exists = path_srv.exists()
                if not path_srv_exists:
                    log.warning("Path doesn't exist: %s", path_srv.as_posix())
            except PermissionError:
                path_srv_exists = False
            if not path_srv_exists:
                paths_content.pop(observer)
                continue
            paths_content[observer] = path_srv

        # paths to direct files, only process of content-directories are avail
        if len(paths_content) > 0:
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

        log.info("Herd finished task execution")

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
        else:
            log.warning("Skipped adding empty result path list")
        if len(paths_content) > 0:
            web_exp.content_paths = paths_content
        else:
            log.warning("Skipped adding empty content path list")
        web_exp.result_size = _size
        web_exp.finished_at = datetime.now(tz=local_tz())
        await web_exp.update_time_start()
        await web_exp.save_changes()

        # send out Mail if user wants it
        if not isinstance(web_exp.owner, Link | User):
            return
        all_done = await WebExperiment.has_scheduled_by_user(web_exp.owner)
        if experiment.email_results or all_done:
            await mail_engine().send_experiment_finished_email(
                web_exp.owner.email, web_exp, all_done=all_done
            )


async def update_status(
    inventory: Path | None = None, *, active: bool = False, dry_run: bool = False
) -> None:
    _client = await db_client()
    tb_ = await TestbedDB.get_one()
    tb_.scheduler.active = active
    tb_.scheduler.dry_run = dry_run
    tb_.scheduler.busy = await WebExperiment.get_next_scheduling() is not None
    tb_.scheduler.last_update = local_now()
    if dry_run:
        tb_.scheduler.observer_count = 0
        tb_.scheduler.observers = None
    else:
        with Herd(inventory=inventory) as herd:
            tb_.scheduler.observer_count = len(herd.group)
            tb_.scheduler.observers = [herd.hostnames[cnx.host] for cnx in herd.group]
    await tb_.save_changes()


async def scheduler(inventory: Path | None = None, *, dry_run: bool = False) -> None:
    _client = await db_client()

    # allow running dry in temp-folder
    with TemporaryDirectory() as temp_dir:
        temp_path: Path = Path(temp_dir)
        log.debug("Temp path: %s", temp_path.resolve())

        if dry_run:
            log.warning("Dry run mode - not executing tasks!")

        # TODO: how to make sure there is only one scheduler? Singleton
        log.info("Checking experiment scheduling FIFO")
        await WebExperiment.reset_stuck_items()

        while True:
            await update_status(inventory=inventory, active=True, dry_run=dry_run)
            next_experiment = await WebExperiment.get_next_scheduling()
            if next_experiment is None:
                log.debug("... waiting 20 s")
                await asyncio.sleep(20)
                continue

            log.debug("NOW scheduling experiment '%s'", next_experiment.experiment.name)
            await run_web_experiment(
                next_experiment.id, inventory=inventory, temp_path=temp_path, dry_run=dry_run
            )


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
