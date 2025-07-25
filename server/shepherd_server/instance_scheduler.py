import asyncio
import time
from contextlib import ExitStack
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from beanie import Link
from pydantic import UUID4
from shepherd_core import Writer as CoreWriter
from shepherd_core import local_now
from shepherd_core.data_models.task import EmulationTask
from shepherd_core.data_models.task import TestbedTasks
from shepherd_core.data_models.testbed import Testbed
from shepherd_herd.herd import Herd

from .api_experiment.models import ReplyData
from .api_experiment.models import WebExperiment
from .api_testbed.models_status import SchedulerStatus
from .api_testbed.models_status import TestbedDB
from .api_user.models import User
from .api_user.utils_mail import mail_engine
from .config import config
from .instance_db import db_available
from .instance_db import db_client
from .logger import log


def tbt_patch_pre(tb_ts: TestbedTasks) -> TestbedTasks:
    tb_ts_pre = tb_ts.model_dump()
    ots_new = []
    for ots in tb_ts_pre.get("observer_tasks"):
        ots["emulation"] = None
        ots_new.append(ots)
    tb_ts_pre["observer_tasks"] = ots_new
    return TestbedTasks(**tb_ts_pre)


def tbt_patch_emu(tb_ts: TestbedTasks, time_start: datetime) -> TestbedTasks:
    tb_ts_emu = tb_ts.model_dump()
    ots_new = []
    for ots in tb_ts_emu.get("observer_tasks"):
        ots["fw1_mod"] = None
        ots["fw1_prog"] = None
        ots["fw2_mod"] = None
        ots["fw2_prog"] = None
        emu_dict = ots.get("emulation")
        if isinstance(emu_dict, EmulationTask):
            ots["emulation"]["time_start"] = time_start
        ots_new.append(ots)
    tb_ts_emu["observer_tasks"] = ots_new
    return TestbedTasks(**tb_ts_emu)


def kill_herd_noasync() -> None:
    with Herd() as herd:
        herd.kill_sheep_process()


def run_herd_noasync(inventory: Path | str | None, tb_tasks: TestbedTasks) -> dict[str, ReplyData]:
    with Herd(inventory=inventory) as herd:
        # Prepare Testbed
        herd.kill_sheep_process()
        # TODO: add target-cleaner (chip erase) - at least flash sleep to avoid program-errors
        while herd.service_is_active():
            time.sleep(20)
        herd.service_erase_log()

        # Prepare Targets
        tasks_pre = tbt_patch_pre(tb_tasks)
        ret = herd.run_task(tasks_pre, attach=False, quiet=True)
        if ret > 0:
            raise RuntimeError("Starting preparation of XP failed")
        while herd.service_is_active():
            time.sleep(20)
        if not herd.service_is_failed():
            # Start Experiment
            herd.start_delay_s = 40
            time_start, delay_s = herd.find_consensus_time()
            log.info(
                "Start XP in %d seconds: %s (obs-time)",
                int(delay_s),
                time_start.isoformat(),
            )
            tasks_emu = tbt_patch_emu(tb_tasks, time_start=time_start)
            ret = herd.run_task(tasks_emu, attach=False, quiet=True)
            if ret > 0:
                raise RuntimeError("Starting Emulation failed")
            while herd.service_is_active():
                time.sleep(20)

        replies = herd.service_get_logs()
    return {
        k: ReplyData(exited=v.exited, stdout=v.stdout, stderr=v.stderr) for k, v in replies.items()
    }


async def run_web_experiment(
    xp_id: UUID4,
    temp_path: Path | None,
    inventory: Path | str | None = None,
    *,
    dry_run: bool = False,
) -> None:
    # mark as started
    web_exp = await WebExperiment.get_by_id(xp_id)
    if web_exp is None:
        log.warning("Dataset of Experiment not found before running it (deleted?)")
        return
    web_exp.started_at = local_now()
    testbed = Testbed(name=config.testbed_name)
    testbed_tasks = TestbedTasks.from_xp(web_exp.experiment, testbed)
    web_exp.observer_paths = testbed_tasks.get_output_paths()
    tb_status = await TestbedDB.get_one()
    web_exp.observers_requested = testbed_tasks.get_observers()
    web_exp.observers_online = tb_status.scheduler.observers_online
    web_exp.observers_offline = tb_status.scheduler.observers_offline
    await web_exp.update_time_start(web_exp.started_at, force=True)
    await web_exp.save_changes()

    if dry_run:
        if temp_path is None:
            raise RuntimeError("Dry-running Scheduler needs a temporary directory")
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
        timeout = web_exp.experiment.duration + timedelta(minutes=10)
        try:
            log.info(
                "NOW starting HERD_RUN() - runtime %d s, timeout in %d s",
                int(web_exp.experiment.duration.total_seconds()),
                int(timeout.total_seconds()),
            )
            replies = await asyncio.wait_for(
                asyncio.to_thread(
                    run_herd_noasync,
                    inventory=inventory,
                    tb_tasks=testbed_tasks,
                ),
                timeout=timeout.total_seconds(),
            )
            log.info("FINISHED HERD_RUN()")
            web_exp.observers_output = replies
            # TODO: detect when experiment was not run (failed early during prep)
            if web_exp.max_exit_code > 0:
                log.error("Herd failed on at least one Observer")
            else:
                log.info("Herd finished task execution successfully")
        except asyncio.TimeoutError:
            log.warning("Timeout waiting for experiment '%s'", web_exp.experiment.name)
            web_exp.scheduler_error = "Timeout waiting for Experiment to finish"
        except Exception:  # noqa: BLE001
            # TODO: send info about the exception
            log.warning("General Exception waiting for experiment '%s'", web_exp.experiment.name)
            web_exp.scheduler_error = "Caught general Exception during Execution"

        if web_exp.scheduler_error is not None:
            await asyncio.wait_for(asyncio.to_thread(kill_herd_noasync), timeout=30)
            await asyncio.sleep(30)  # finish IO, precaution
        await asyncio.sleep(20)  # finish IO, precaution
        web_exp.finished_at = local_now()
        await web_exp.update_time_start()
        await web_exp.update_result()
        await web_exp.save_changes()
        await notify_user(web_exp.id)

        # Reload XP to avoid race-condition / working on old data
        web_exp = await WebExperiment.get_by_id(xp_id)
        if web_exp is None:
            log.warning("Dataset of Experiment not found after running it (deleted?)")
            return


async def notify_user(xp_id: UUID4) -> None:
    web_exp = await WebExperiment.get_by_id(xp_id)
    if web_exp is None:
        log.warning("Dataset of Experiment not found before running it (deleted?)")
        return

    # send out Mail if user wants it
    if web_exp.had_errors or not isinstance(web_exp.owner, Link | User):
        await mail_engine().send_experiment_finished_email(config.contact["email"], web_exp)
        return
    all_done = not await WebExperiment.has_scheduled_by_user(web_exp.owner)
    if web_exp.had_errors or web_exp.experiment.email_results or all_done:
        await mail_engine().send_experiment_finished_email(
            web_exp.owner.email, web_exp, all_done=all_done
        )


def update_status_noasync(stat: SchedulerStatus) -> SchedulerStatus:
    with Herd() as herd:  # inventory shouldn't be needed here
        stat.observer_count = len(herd.group)
        stat.observers_online = {herd.hostnames[cnx.host] for cnx in herd.group}
        stat.observers_offline = set(herd.hostnames.values()) - stat.observers_online
    return stat


async def update_status(*, active: bool = False, dry_run: bool = False) -> None:
    _client = await db_client()
    tb_ = await TestbedDB.get_one()
    tb_.scheduler.dry_run = dry_run
    tb_.scheduler.busy = await WebExperiment.get_next_scheduling() is not None
    tb_.scheduler.last_update = local_now()
    if not active:
        tb_.scheduler.activated = None
    if dry_run:
        tb_.scheduler.observer_count = 0
        tb_.scheduler.observers_online = set()
        tb_.scheduler.observers_offline = set()
    else:
        tb_.scheduler = await asyncio.wait_for(
            asyncio.to_thread(update_status_noasync, tb_.scheduler), timeout=30
        )
    # TODO: include storage, warn via mail if low
    await tb_.save_changes()


async def scheduler(
    inventory: Path | None = None,
    *,
    dry_run: bool = False,
    only_elevated: bool = False,
) -> None:
    _client = await db_client()
    tb_ = await TestbedDB.get_one()
    tb_.scheduler.activated = local_now()
    await tb_.save_changes()

    # allow running dry in temp-folder
    with ExitStack() as stack:
        temp_path: Path | None = None
        if dry_run:
            temp_dir = TemporaryDirectory(suffix="srv_scheduler_")
            stack.enter_context(temp_dir)
            temp_path: Path = Path(temp_dir)
            log.debug("Temp path: %s", temp_path.resolve())
            log.warning("Dry run mode - not executing tasks!")

        # TODO: how to make sure there is only one scheduler? Singleton
        log.info("Checking experiment scheduling FIFO")
        await WebExperiment.reset_stuck_items()

        while True:
            await update_status(active=True, dry_run=dry_run)
            # TODO: status could generate usable inventory, so missing nodes
            next_experiment = await WebExperiment.get_next_scheduling(only_elevated=only_elevated)
            if next_experiment is None:
                log.debug("... waiting 20 s")
                await asyncio.sleep(20)
                continue

            log.debug("NOW scheduling experiment '%s'", next_experiment.experiment.name)
            await run_web_experiment(
                next_experiment.id,
                inventory=inventory,
                temp_path=temp_path,
                dry_run=dry_run,
            )


def run(
    inventory: Path | None = None, *, dry_run: bool = False, only_elevated: bool = False
) -> None:
    if not db_available(timeout=5):
        log.error("No connection to database! Will exit scheduler now.")
        return

    try:
        asyncio.run(scheduler(inventory, dry_run=dry_run, only_elevated=only_elevated))
    except OSError:
        log.exception("Error while running scheduler - probably Paramiko/SSH Overflow.")
    except SystemExit:
        log.info("Exit-Signal received, Scheduler is now stopped.")

    asyncio.run(update_status(dry_run=dry_run))


if __name__ == "__main__":
    run()
