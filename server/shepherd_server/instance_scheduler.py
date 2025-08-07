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


def cleanup_herd_noasync(herd: Herd) -> None:
    herd.open()
    herd.kill_sheep_process()
    # TODO: add target-cleaner (chip erase) - at least flash sleep to avoid program-errors
    while herd.service_is_active():
        time.sleep(8)
    herd.service_erase_log()


def run_herd_noasync(herd: Herd, tb_tasks: TestbedTasks) -> dict[str, ReplyData]:
    # Prepare Targets
    tasks_pre = tbt_patch_pre(tb_tasks)
    ret = herd.run_task(tasks_pre, attach=False, quiet=True)
    if ret > 0:
        raise RuntimeError("Starting preparation of targets failed")
    while herd.service_is_active():
        time.sleep(20)
    if herd.service_is_failed():
        log.warning("Preparation of targets failed - will skip XP")
    else:  # Start Experiment
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
    herd: Herd | None,
) -> None:
    # TODO: save timestamp for getting service-log
    log.info("HERD_RUN(id=%s)", str(xp_id))
    # mark as started
    web_exp = await WebExperiment.get_by_id(xp_id)
    if web_exp is None:
        log.warning("XP-dataset not found before running it (deleted?)")
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

    if isinstance(herd, Herd):
        timeout = web_exp.experiment.duration + timedelta(minutes=10)
        replies = {}

        try:
            log.info("  .. preparation")
            await asyncio.wait_for(
                asyncio.to_thread(cleanup_herd_noasync, herd=herd),
                timeout=60,
            )
            # only utilize nodes that online and requested
            herd.group_online = [
                cnx
                for cnx in herd.group_online
                if herd.hostnames[cnx.host] in web_exp.observers_requested
            ]
            log.info(
                "  .. now starting - runtime %d s, timeout in %d s, %d of %d observers",
                int(web_exp.experiment.duration.total_seconds()),
                int(timeout.total_seconds()),
                len(herd.group_online),
                len(herd.group_all),
            )
            replies = await asyncio.wait_for(
                asyncio.to_thread(
                    run_herd_noasync,
                    herd=herd,
                    tb_tasks=testbed_tasks,
                ),
                timeout=timeout.total_seconds(),
            )
            log.info("  .. cleanup")
            await asyncio.sleep(30)  # finish IO, precaution
            await asyncio.wait_for(
                asyncio.to_thread(cleanup_herd_noasync, herd=herd),
                timeout=60,
            )
            await asyncio.sleep(30)  # stabilize

        except asyncio.TimeoutError:
            log.warning("Timeout waiting for experiment '%s'", web_exp.experiment.name)
            scheduler_error = "Timeout waiting for Experiment to finish"
        except Exception as xpt:  # noqa: BLE001
            log.warning("General Exception waiting for experiment '%s'", web_exp.experiment.name)
            scheduler_error = f"Caught general Exception during Execution ({xpt})"
        else:
            scheduler_error = None

        log.info("  .. finished - now collecting data")
        # Reload XP to avoid race-condition / working on old data
        web_exp = await WebExperiment.get_by_id(xp_id)
        if web_exp is None:
            log.warning("XP-dataset not found after running it (deleted?)")
            return

        web_exp.finished_at = local_now()
        web_exp.observers_output = replies
        web_exp.scheduler_error = scheduler_error
        if len(web_exp.observers_output) == 0:
            log.error("Herd collected no logs from node (")
        if web_exp.max_exit_code > 0:
            log.error("Herd failed on at least one Observer")

        await web_exp.update_time_start()
        await web_exp.update_result()
        await web_exp.save_changes()
        await notify_user(web_exp.id)
        log.info("  .. users were informed")
        await asyncio.sleep(60)  # stabilize

    else:  # dry run
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


async def update_status(herd: Herd | None = None, *, active: bool = False) -> None:
    _client = await db_client()
    tb_ = await TestbedDB.get_one()
    tb_.scheduler.dry_run = not isinstance(herd, Herd)
    tb_.scheduler.busy = await WebExperiment.get_next_scheduling() is not None
    tb_.scheduler.last_update = local_now()
    if not active:
        tb_.scheduler.activated = None
    if isinstance(herd, Herd):
        await asyncio.wait_for(asyncio.to_thread(herd.open), timeout=30)
        tb_.scheduler.observer_count = len(herd.group_online)
        tb_.scheduler.observers_online = {herd.hostnames[cnx.host] for cnx in herd.group_online}
        tb_.scheduler.observers_offline = (
            set(herd.hostnames.values()) - tb_.scheduler.observers_online
        )
    else:  # dry run or offline
        tb_.scheduler.observer_count = 0
        tb_.scheduler.observers_online = set()
        tb_.scheduler.observers_offline = set()

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
            herd = None
        else:
            herd = Herd(inventory=inventory)
            stack.enter_context(herd)

        # TODO: how to make sure there is only one scheduler? Singleton
        log.info("Checking experiment scheduling FIFO")
        await WebExperiment.reset_stuck_items()

        while True:
            await update_status(herd=herd, active=True)
            # TODO: status could generate usable inventory, so missing nodes
            next_experiment = await WebExperiment.get_next_scheduling(only_elevated=only_elevated)
            if next_experiment is None:
                log.debug("... waiting 20 s")
                await asyncio.sleep(20)
                continue

            log.debug("NOW scheduling experiment '%s'", next_experiment.experiment.name)
            await run_web_experiment(
                next_experiment.id,
                temp_path=temp_path,
                herd=herd,
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

    asyncio.run(update_status())


if __name__ == "__main__":
    run()
