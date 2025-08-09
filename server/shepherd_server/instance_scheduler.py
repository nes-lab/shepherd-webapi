import asyncio
import subprocess
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


def cleanup_herd_syn(herd: Herd) -> None:
    herd.open()
    herd.kill_sheep_process()
    # TODO: add target-cleaner (chip erase) - at least flash sleep to avoid program-errors
    while herd.service_is_active():
        time.sleep(8)
    herd.service_erase_log()


async def cleanup_herd(herd: Herd, *, pre: bool = False) -> str | None:
    timeout = 60
    reason = "preparation" if pre else "finalization"
    try:
        await asyncio.wait_for(
            asyncio.to_thread(cleanup_herd_syn, herd=herd),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        error_msg = f"Timeout ({timeout} s) waiting for {reason}-cleanup"
    except Exception as xpt:  # noqa: BLE001
        error_msg = f"Caught general Exception during {reason}-cleanup ({xpt})"
    else:
        error_msg = None
    await asyncio.sleep(10)  # stabilize
    return error_msg


def prepare_herd_xp_syn(herd: Herd, tb_tasks: TestbedTasks) -> None:
    pre_tasks = tbt_patch_pre(tb_tasks)
    ret = herd.run_task(pre_tasks, attach=False, quiet=True)
    if ret > 0:
        raise RuntimeError("Starting preparation of targets failed")
    while herd.service_is_active():
        time.sleep(20)
    if herd.service_is_failed():
        raise RuntimeError("Preparation of targets failed - will skip XP")


async def prepare_herd_xp(herd: Herd, tb_tasks: TestbedTasks) -> str | None:
    timeout = 5 * 60
    try:
        await asyncio.wait_for(
            asyncio.to_thread(prepare_herd_xp_syn, herd=herd, tb_tasks=tb_tasks),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        error_msg = f"Timeout ({timeout} s) waiting for preparing experiment"
    except RuntimeError as xpt:
        error_msg = f"Caught runtime error ({xpt}) preparing experiment"
    except Exception as xpt:  # noqa: BLE001
        error_msg = f"Caught general exception preparing experiment ({xpt})"
    else:
        error_msg = None
    await asyncio.sleep(10)  # stabilize
    return error_msg


def execute_herd_xp_syn(herd: Herd, tb_tasks: TestbedTasks) -> None:
    time_start, delay_s = herd.find_consensus_time()
    log.info(
        "  .. waiting %d seconds: %s (obs-time)",
        int(delay_s),
        time_start.isoformat(),
    )
    tasks_emu = tbt_patch_emu(tb_tasks, time_start=time_start)
    ret = herd.run_task(tasks_emu, attach=False, quiet=True)
    if ret > 0:
        raise RuntimeError("Starting Emulation failed")
    while herd.service_is_active():
        time.sleep(20)


async def execute_herd_xp(herd: Herd, tb_tasks: TestbedTasks, timeout: timedelta) -> str | None:
    try:
        await asyncio.wait_for(
            asyncio.to_thread(prepare_herd_xp_syn, herd=herd, tb_tasks=tb_tasks),
            timeout=timeout.total_seconds(),
        )
    except asyncio.TimeoutError:
        error_msg = f"Timeout ({timeout} hms) waiting for experiment to finish"
    except RuntimeError as xpt:
        error_msg = f"Caught runtime error ({xpt}) during experiment"
    except Exception as xpt:  # noqa: BLE001
        error_msg = f"Caught general exception during experiment ({xpt})"
    else:
        error_msg = None
    await asyncio.sleep(10)  # stabilize
    return error_msg


def fetch_herd_logs_syn(herd: Herd) -> dict[str, ReplyData]:
    replies = herd.service_get_logs()
    return {
        k: ReplyData(exited=v.exited, stdout=v.stdout, stderr=v.stderr) for k, v in replies.items()
    }


async def fetch_herd_logs(herd: Herd, xp_id: UUID4) -> str | None:
    timeout = 30
    replies = {}
    try:
        replies = await asyncio.wait_for(
            asyncio.to_thread(fetch_herd_logs_syn, herd=herd),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        error_msg = f"Timeout ({timeout} s) waiting for herd-logs"
    except RuntimeError as xpt:
        error_msg = f"Caught runtime error ({xpt}) getting herd-logs"
    except Exception as xpt:  # noqa: BLE001
        error_msg = f"Caught general exception getting herd-logs ({xpt})"
    else:
        error_msg = None

    web_exp = await WebExperiment.get_by_id(xp_id)
    if web_exp is None:
        log.warning("XP-dataset not found (deleted?) for fetching herd-log")
    else:
        web_exp.observers_output = replies
        await web_exp.save_changes()
    await asyncio.sleep(10)  # stabilize
    return error_msg


def fetch_scheduler_log_syn(ts_start: datetime) -> str | None:
    command = [
        "/usr/bin/journalctl",
        "--unit=shepherd-scheduler",
        "--output=short-iso-precise",
        "--no-pager",
        "--utc",
        "--all",  # includes unprintable chars and message-chunks?
        "--quiet",  # avoid non-sudo warning
        "--since",
        ts_start.isoformat(sep=" ")[:16],
        # "--priority", "emerg..info",  # does NOT reduce tqdm output
    ]
    # TODO: use queue for logger
    ret = subprocess.run(  # noqa: S603
        command,
        timeout=10,
        stdout=subprocess.PIPE,
        text=True,
        check=False,
    )
    if ret.returncode != 0:
        log.warning("Trouble getting scheduler log: %s", ret.stderr)
    return ret.stdout


async def fetch_scheduler_log(xp_id: UUID4, ts_start: datetime) -> str | None:
    timeout = 20
    reply = None
    try:
        reply = await asyncio.wait_for(
            asyncio.to_thread(fetch_scheduler_log_syn, ts_start=ts_start),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        error_msg = f"Timeout ({timeout} s) waiting for scheduler-log"
    except RuntimeError as xpt:
        error_msg = f"Caught runtime error ({xpt}) getting scheduler-log"
    except Exception as xpt:  # noqa: BLE001
        error_msg = f"Caught general exception getting scheduler-log ({xpt})"
    else:
        error_msg = None

    web_exp = await WebExperiment.get_by_id(xp_id)
    if web_exp is None:
        log.warning("XP-dataset not found (deleted?) for fetching scheduler log")
    else:
        web_exp.scheduler_log = reply
        await web_exp.save_changes()
    return error_msg


def reboot_herd_syn(herd: Herd) -> set:
    herd.open()
    _pre = set(herd.group_online)

    herd.reboot()  # TODO: add sysrq-reboot
    time.sleep(120)

    herd.open()
    _try = 0
    while _try < 6 and len(_pre) > len(herd.group_online):
        time.sleep(10)
        _try += 1
        herd.open()
    log.info("Rebooting brought back %d of %d observers", len(herd.group_online), len(_pre))
    return _pre


async def reboot_herd(herd: Herd) -> None:
    timeout = 200
    group_pre = set()
    try:
        group_pre = await asyncio.wait_for(
            asyncio.to_thread(reboot_herd_syn, herd=herd),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        log.warning("Timeout waiting for reboot of herd")
    composition = {
        "all": {herd.hostnames[cnx.host] for cnx in herd.group_all},
        "pre": {herd.hostnames[cnx.host] for cnx in group_pre},
        "post": {herd.hostnames[cnx.host] for cnx in herd.group_online},
    }
    await mail_engine().send_herd_reboot_email(composition)


async def run_web_experiment(
    xp_id: UUID4,
    temp_path: Path | None,
    herd: Herd | None,
) -> None:
    ts_start = datetime.now()  # noqa: DTZ005
    log.info("HERD_RUN(id=%s)", str(xp_id))
    # mark as started
    web_exp = await WebExperiment.get_by_id(xp_id)
    if web_exp is None:
        log.warning("XP-dataset not found (deleted?) before running it")
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
        log.info("  .. pre-cleanup")
        _err1 = await cleanup_herd(herd, pre=True)

        if _err1 is None:
            # only utilize nodes that online and requested
            herd.group_online = [
                cnx
                for cnx in herd.group_online
                if herd.hostnames[cnx.host] in web_exp.observers_requested
            ]
            log.info("  .. preparation")
            _err1 = await prepare_herd_xp(herd, testbed_tasks)

        ts_exe = None
        if _err1 is None:
            timeout = web_exp.experiment.duration + timedelta(minutes=10)
            delay_exe = timedelta(seconds=60)  # to better synchronize start
            herd.start_delay_s = delay_exe.total_seconds()
            log.info(
                "  .. now executing - runtime %d s, timeout in %d s, %d of %d observers",
                int(web_exp.experiment.duration.total_seconds()),
                int(timeout.total_seconds()),
                len(herd.group_online),
                len(herd.group_all),
            )
            ts_exe = local_now() + delay_exe
            _err1 = await execute_herd_xp(herd, testbed_tasks, timeout)

        if _err1 is not None:
            log.warning(_err1)

        log.info("  .. retrieve logs")
        await asyncio.sleep(30)  # finish IO, precaution
        _err2 = await fetch_herd_logs(herd, xp_id)
        if _err2 is not None:
            log.warning(_err2)

        log.info("  .. post-cleanup")
        _err3 = await cleanup_herd(herd, pre=False)
        if _err3 is not None:
            log.warning(_err3)
        await asyncio.sleep(30)  # stabilize

        log.info("  .. finished - now collecting data")
        # Reload XP to avoid race-condition / working on old data
        web_exp = await WebExperiment.get_by_id(xp_id)
        if web_exp is None:
            log.warning("XP-dataset not found (deleted?) after running it (deleted?)")
            return

        web_exp.executed_at = ts_exe
        web_exp.finished_at = local_now()
        web_exp.scheduler_error = _err1 or _err2 or _err3

        if len(web_exp.observers_output) == 0:
            log.error("Herd collected no logs from node (")
        if web_exp.max_exit_code > 0:
            log.error("Herd failed on at least one Observer")

        await web_exp.update_time_start()
        await web_exp.update_result()
        await web_exp.save_changes()
        await fetch_scheduler_log(xp_id=xp_id, ts_start=ts_start)
        await notify_user(web_exp.id)
        log.info("  .. users were informed")
        if web_exp.had_errors:
            log.info("  .. herd-reboot due to errors")
            await reboot_herd(herd)
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
        log.warning("XP-dataset not found (deleted?) for email-notification")
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
