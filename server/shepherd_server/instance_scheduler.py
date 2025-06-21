import asyncio
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from pathlib import PurePosixPath
from tempfile import TemporaryDirectory

import numpy as np
from beanie import Link
from pydantic import UUID4
from shepherd_core import Writer as CoreWriter
from shepherd_core import local_now
from shepherd_core import local_tz
from shepherd_core.data_models.task import EmulationTask
from shepherd_core.data_models.task import TestbedTasks
from shepherd_core.data_models.testbed import Testbed
from shepherd_herd.herd import Herd

from .api_experiment.models import ReplyData
from .api_experiment.models import WebExperiment
from .api_testbed.models_status import TestbedDB
from .api_user.models import User
from .api_user.utils_mail import mail_engine
from .config import config
from .instance_db import db_available
from .instance_db import db_client
from .logger import log


def tbt_patch_time_start(tb_ts: TestbedTasks, time_start: datetime) -> TestbedTasks:
    tb_ts_dict = tb_ts.model_dump()
    ots_new = []
    for ots in tb_ts_dict.get("observer_tasks"):
        emu_dict = ots.get("emulation")
        if isinstance(emu_dict, EmulationTask):
            ots["emulation"]["time_start"] = time_start
        ots_new.append(ots)
    tb_ts_dict["observer_tasks"] = ots_new
    return TestbedTasks(**tb_ts_dict)


async def run_web_experiment(
    xp_id: UUID4, temp_path: Path, inventory: Path | str | None = None, *, dry_run: bool = False
) -> None:
    # mark as started
    web_exp = await WebExperiment.get_by_id(xp_id)
    if web_exp is None:
        log.warning("Dataset of Experiment not found before running it (deleted?)")
        return
    web_exp.started_at = datetime.now(tz=local_tz())
    testbed = Testbed(name=config.testbed_name)
    testbed_tasks = TestbedTasks.from_xp(web_exp.experiment, testbed)
    web_exp.observer_paths = testbed_tasks.get_output_paths()
    await web_exp.save_changes()
    log.info("Starting Testbed-tasks through Herd-tool")

    if dry_run:
        await asyncio.sleep(10)  # mocked length
        # create mocked files
        paths_task = testbed_tasks.get_output_paths()
        paths_result: dict[str, Path] = {}
        xp_folder = web_exp.experiment.folder_name()
        for name, path_task in paths_task.items():
            paths_result[name] = temp_path / xp_folder / path_task.name
            with CoreWriter(paths_result[name]) as writer:
                writer.store_hostname(name)
                writer.append_iv_data_si(
                    timestamp=local_now().timestamp(),
                    voltage=np.zeros(10_000),
                    current=np.zeros(10_000),
                )
        await web_exp.update_result(paths_result)
    else:
        with Herd(inventory=inventory) as herd:
            web_exp.observers_list = list(herd.hostnames.values())
            web_exp.observers_used = [herd.hostnames[cnx.host] for cnx in herd.group]
            await web_exp.update_time_start(local_now())
            await web_exp.save_changes()
            # force other sheep-instances to end
            herd.run_cmd(sudo=True, cmd="pkill shepherd-sheep")

            # TODO: add target-cleaner (chip erase) - at least flash sleep
            # TODO: add missing nodes to error-log of web_exp

            # below is a modified herd.run_task(testbed_tasks, attach=True, quiet=True)
            remote_path = PurePosixPath("/etc/shepherd/config_for_herd.pickle")
            # TODO: this is a workaround to force synced start
            #       it wastes time but keeps logs of pre-tasks (programming) in result-file
            herd.start_delay_s = 5 * 60  # testbed.prep_duration.total_seconds()
            time_start, delay_s = herd.find_consensus_time()
            log.info(
                "Experiment will start in %d seconds: %s (obs-time)",
                delay_s,
                time_start.isoformat(),
            )
            testbed_tasks = tbt_patch_time_start(testbed_tasks, time_start=time_start)
            herd.put_task(task=testbed_tasks, remote_path=remote_path)
            command = f"shepherd-sheep --verbose run {remote_path.as_posix()}"
            replies = herd.run_cmd(sudo=True, cmd=command)
            # TODO: this can lock - not the best approach, try asyncio.wait_for()

        exit_code = max([0] + [abs(reply.exited) for reply in replies.values()])
        if exit_code > 0:
            log.error("Herd failed on at least one Observer")
        else:
            log.info("Herd finished task execution successfully")

        await asyncio.sleep(20)  # finish IO, precaution

        # Reload XP to avoid race-condition / working on old data
        web_exp = await WebExperiment.get_by_id(xp_id)
        if web_exp is None:
            log.warning("Dataset of Experiment not found after running it (deleted?)")
            return

        # paths to directories with all content like firmware, h5-results, ...
        web_exp.observers_output = {
            k: ReplyData(exited=v.exited, stdout=v.stdout, stderr=v.stderr)
            for k, v in replies.items()
        }
        web_exp.finished_at = datetime.now(tz=local_tz())
        await web_exp.save_changes()
        await web_exp.update_result()
        await web_exp.update_time_start()


async def notify_user(xp_id: UUID4) -> None:
    web_exp = await WebExperiment.get_by_id(xp_id)
    if web_exp is None:
        log.warning("Dataset of Experiment not found before running it (deleted?)")
        return

    # send out Mail if user wants it
    if web_exp.had_errors or not isinstance(web_exp.owner, Link | User):
        await mail_engine().send_experiment_finished_email(config.contact["email"], web_exp)
        return
    all_done = await WebExperiment.has_scheduled_by_user(web_exp.owner)
    if web_exp.had_errors or web_exp.experiment.email_results or all_done:
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
        with Herd(inventory=inventory) as herd:  # inventory shouldn't be needed here
            tb_.scheduler.observer_count = len(herd.group)
            tb_.scheduler.observers = [herd.hostnames[cnx.host] for cnx in herd.group]
    # TODO: include storage, warn via mail if low
    await tb_.save_changes()


async def scheduler(
    inventory: Path | None = None,
    *,
    dry_run: bool = False,
    only_elevated: bool = False,
) -> None:
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
            # TODO: status could generate usable inventory, so missing nodes
            next_experiment = await WebExperiment.get_next_scheduling(only_elevated=only_elevated)
            if next_experiment is None:
                log.debug("... waiting 20 s")
                await asyncio.sleep(20)
                continue

            log.debug("NOW scheduling experiment '%s'", next_experiment.experiment.name)
            timeout = next_experiment.experiment.duration + timedelta(minutes=10)
            try:
                await asyncio.wait_for(
                    run_web_experiment(
                        next_experiment.id,
                        inventory=inventory,
                        temp_path=temp_path,
                        dry_run=dry_run,
                    ),
                    timeout=timeout.total_seconds(),
                )
            except asyncio.TimeoutError:
                # TODO: test
                log.warning("Timeout waiting for experiment '%s'", next_experiment.experiment.name)
                next_experiment.finished_at = datetime.now(tz=local_tz())
                await next_experiment.update_result()
                await next_experiment.update_time_start()
            except Exception:  # noqa: BLE001
                # TODO: send info about the exception
                next_experiment.scheduler_panic = True
                next_experiment.save_changes()
            await notify_user(next_experiment.id)


def run(
    inventory: Path | None = None, *, dry_run: bool = False, only_elevated: bool = False
) -> None:
    if not db_available(timeout=5):
        log.error("No connection to database! Will exit scheduler now.")
        return

    try:
        asyncio.run(scheduler(inventory, dry_run=dry_run, only_elevated=only_elevated))
    except SystemExit:
        asyncio.run(update_status(inventory, dry_run=dry_run))


if __name__ == "__main__":
    run()
