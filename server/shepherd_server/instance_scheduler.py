import asyncio
import subprocess
import time
from contextlib import ExitStack
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

import numpy as np
from beanie import Link
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
from .async_wrapper import async_wrap
from .config import config
from .instance_db import db_available
from .instance_db import db_client
from .logger import log

# TODO:
#   - auto-retry sub-tasks or whole job after it failed
#   - refactor complex herd-fn into sep file


@async_wrap(timeout=60)
def herd_cleanup(herd: Herd) -> None:
    herd.open()
    herd.kill_sheep_process()
    # TODO: add target-cleaner (chip erase) - at least flash sleep to avoid program-errors
    while herd.service_is_active():
        time.sleep(8)
    herd.service_erase_log()


@async_wrap(timeout=5 * 60)
def herd_prepare_experiment(herd: Herd, tb_tasks: TestbedTasks) -> None:
    def tbt_patch_pre(tb_ts: TestbedTasks) -> TestbedTasks:
        tb_ts_pre = tb_ts.model_dump()
        ots_new = []
        for ots in tb_ts_pre.get("observer_tasks"):
            ots["emulation"] = None
            ots_new.append(ots)
        tb_ts_pre["observer_tasks"] = ots_new
        return TestbedTasks(**tb_ts_pre)

    pre_tasks = tbt_patch_pre(tb_tasks)
    ret = herd.run_task(pre_tasks, attach=False, quiet=True)
    if ret > 0:
        raise RuntimeError("Starting preparation of targets failed")
    while herd.service_is_active():
        time.sleep(11)
    if herd.service_is_failed():
        raise RuntimeError("Preparation of targets failed - will skip XP")


@async_wrap(timeout=30)
def herd_schedule_experiment(herd: Herd, tb_tasks: TestbedTasks) -> None:
    def tbt_patch_emu(tb_ts: TestbedTasks, ts_start: datetime) -> TestbedTasks:
        tb_ts_emu = tb_ts.model_dump()
        ots_new = []
        for ots in tb_ts_emu.get("observer_tasks"):
            ots["fw1_mod"] = None
            ots["fw1_prog"] = None
            ots["fw2_mod"] = None
            ots["fw2_prog"] = None
            emu_dict = ots.get("emulation")
            if isinstance(emu_dict, EmulationTask):
                ots["emulation"]["time_start"] = ts_start
            ots_new.append(ots)
        tb_ts_emu["observer_tasks"] = ots_new
        return TestbedTasks(**tb_ts_emu)

    time_start, delay_s = herd.find_consensus_time()
    log.info(
        "  .. waiting %d seconds: %s (obs-time)",
        int(delay_s),
        time_start.isoformat(sep=" ")[:19],
    )
    tasks_emu = tbt_patch_emu(tb_tasks, ts_start=time_start)
    ret = herd.run_task(tasks_emu, attach=False, quiet=True)
    if ret > 0:
        raise RuntimeError("Starting Emulation failed")


async def herd_wait_completion(herd: Herd, timeout: timedelta) -> str | None:
    # this fn can not be wrapped, because it has no fixed timeout
    # TODO: add to main code?
    ts_timeout = local_now() + timeout
    error_msg = None
    try:
        while await asyncio.wait_for(asyncio.to_thread(herd.service_is_active), timeout=30):
            if local_now() > ts_timeout:
                error_msg = f"Timeout ({timeout} hms) waiting for experiment to complete"
                break
            await asyncio.sleep(21)
    except asyncio.TimeoutError:
        error_msg = "Timeout waiting for experiment-status during execution"
    return error_msg


@async_wrap(timeout=30)
def herd_fetch_timestamp(herd: Herd) -> datetime:
    return min(herd.get_local_timestamps()) - timedelta(minutes=2)


@async_wrap(timeout=30)
def herd_fetch_logs(herd: Herd, since: datetime) -> dict[str, ReplyData]:
    replies = herd.service_get_logs(since=since)
    return {
        k: ReplyData(exited=v.exited, stdout=v.stdout, stderr=v.stderr) for k, v in replies.items()
    }


@async_wrap(timeout=30)
def fetch_scheduler_log(ts_start: datetime) -> str | None:
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


def herd_reboot_syn(herd: Herd) -> set:
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

    return _pre


async def herd_reboot(herd: Herd) -> None:
    group_pre = set()
    try:
        log.info("Rebooting herd NOW!")
        group_pre = await asyncio.wait_for(
            asyncio.to_thread(herd_reboot_syn, herd=herd),
            timeout=200,
        )
        delay = 5 * 60
        log.info("  .. give PTP %d s to stabilize", delay)
        await asyncio.sleep(delay)  # stabilize PTP
        await asyncio.wait_for(asyncio.to_thread(herd.open), timeout=30)
        log.info("  .. brought back %d of %d observers", len(herd.group_online), len(group_pre))
    except asyncio.TimeoutError:
        log.warning("Timeout waiting for reboot of herd")
    composition = {
        "all": {herd.hostnames[cnx.host] for cnx in herd.group_all},
        "pre": {herd.hostnames[cnx.host] for cnx in group_pre},
        "post": {herd.hostnames[cnx.host] for cnx in herd.group_online},
    }
    await mail_engine().send_herd_reboot_email(composition)


async def run_web_experiment(
    xp_id: UUID,
    temp_path: Path | None,
    herd: Herd | None,
) -> bool:
    had_error = False
    ts_start = datetime.now()  # noqa: DTZ005
    log.info("HERD_RUN(id=%s)", str(xp_id))
    # mark as started
    web_exp = await WebExperiment.get_by_id(xp_id)
    if web_exp is None:
        log.warning("XP-dataset not found (deleted?) before running it")
        return had_error
    web_exp.started_at = local_now()
    testbed = Testbed(name=config.testbed_name)
    testbed_tasks = TestbedTasks.from_xp(web_exp.experiment, testbed)
    web_exp.observer_paths = testbed_tasks.get_output_paths()
    tb_status = await TestbedDB.get_one()
    web_exp.observers_requested = sorted(testbed_tasks.get_observers())
    web_exp.observers_online = sorted(tb_status.scheduler.observers_online)
    web_exp.observers_offline = sorted(tb_status.scheduler.observers_offline)
    await web_exp.update_time_start(web_exp.started_at, force=True)
    await web_exp.save_changes()

    if isinstance(herd, Herd):
        # only utilize nodes that online and requested
        herd.group_online = [
            cnx
            for cnx in herd.group_online
            if herd.hostnames[cnx.host] in web_exp.observers_requested
        ]
        log.info("  .. preparation")
        ts_herd, _err1 = await herd_fetch_timestamp(herd)
        if _err1 is None:
            _, _err1 = await herd_prepare_experiment(herd, testbed_tasks)
            await asyncio.sleep(30)  # stabilize

        exe_timestamp = None
        exe_delay = timedelta(seconds=60)  # to better synchronize start
        exe_timeout = web_exp.experiment.duration + timedelta(minutes=10)
        if _err1 is None:
            herd.start_delay_s = exe_delay.total_seconds()
            log.info(
                "  .. now executing - runtime %s hms, timeout in %s hms, %d of %d observers",
                str(web_exp.experiment.duration),
                str(exe_timeout),
                len(herd.group_online),
                len(herd.group_all),
            )
            exe_timestamp = local_now() + exe_delay
            _, _err1 = await herd_schedule_experiment(herd, testbed_tasks)

        if _err1 is None:
            log.info("  .. waiting for completion")
            _err1 = await herd_wait_completion(herd, exe_timeout)
        else:
            log.warning(_err1)

        log.info("  .. retrieve logs")
        await asyncio.sleep(30)  # finish IO, precaution
        log_herd, _err2 = await herd_fetch_logs(herd, since=ts_herd)
        if _err2 is not None:
            log.warning(_err2)

        log.info("  .. cleanup")
        t, _err3 = await herd_cleanup(herd)  # will also re-add all online observers
        if _err3 is not None:
            log.warning(_err3)

        log.info("  .. finished - now collecting data")
        # Reload XP to avoid race-condition / working on old data
        web_exp = await WebExperiment.get_by_id(xp_id)
        if web_exp is None:
            log.warning("XP-dataset not found (deleted?) after running it (deleted?)")
            return (_err1 or _err2 or _err3) is not None

        if log_herd is not None:
            web_exp.observers_output = log_herd
        web_exp.executed_at = exe_timestamp
        web_exp.finished_at = local_now()
        web_exp.scheduler_error = _err1 or _err2 or _err3

        if len(web_exp.observers_output) == 0:
            log.error("Herd collected no logs from node (")
        if web_exp.max_exit_code > 0:
            log.error("Herd failed on at least one Observer")

        await web_exp.update_time_start(web_exp.executed_at, force=True)
        # await web_exp.update_time_start()
        # take from files if possible, BUT has time of observer
        await web_exp.update_result()
        web_exp.scheduler_log, _ = await fetch_scheduler_log(ts_start=ts_start)
        await web_exp.save_changes()
        await notify_user(web_exp.id)
        log.info("  .. users were informed")
        had_error = web_exp.had_errors

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
    return had_error


async def notify_user(xp_id: UUID) -> None:
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
        tb_.scheduler.observers_online = sorted(
            herd.hostnames[cnx.host] for cnx in herd.group_online
        )
        tb_.scheduler.observers_offline = sorted(
            set(herd.hostnames.values()) - set(tb_.scheduler.observers_online)
        )
    else:  # dry run or offline
        tb_.scheduler.observer_count = 0
        tb_.scheduler.observers_online = []
        tb_.scheduler.observers_offline = []

    # TODO: include storage & uptime, warn via mail if low
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
    wait_delay: int = 20

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
            stack.enter_context(herd)  # TODO: this is not async
            herd.disable_progress_bar()
            log.info("Run initial herd-cleanup")
            await herd_cleanup(herd)

        # TODO: how to make sure there is only one scheduler? Singleton
        log.info("Checking experiment scheduling FIFO")
        await WebExperiment.reset_stuck_items()

        while True:
            await update_status(herd=herd, active=True)

            next_experiment = await WebExperiment.get_next_scheduling(only_elevated=only_elevated)
            if next_experiment is None:
                log.debug("... waiting %d s", wait_delay)
                await asyncio.sleep(wait_delay)
                continue

            log.debug("NOW scheduling experiment '%s'", next_experiment.experiment.name)
            had_error = await run_web_experiment(
                next_experiment.id,
                temp_path=temp_path,
                herd=herd,
            )
            if had_error:
                log.info("  .. herd-reboot due to errors (scheduler will quit / restart after)")
                await herd_reboot(herd)
                return


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
        log.info("Exit-Signal received.")

    log.info("Scheduler will now shut down.")
    asyncio.run(update_status())


if __name__ == "__main__":
    run()
