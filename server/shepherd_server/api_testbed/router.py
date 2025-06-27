import asyncio
import subprocess
from pathlib import Path

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Response
from shepherd_core.data_models.testbed import Testbed
from shepherd_herd import Herd

from shepherd_server.api_testbed.models_status import TestbedDB
from shepherd_server.api_user.utils_misc import active_user_is_admin
from shepherd_server.api_user.utils_misc import active_user_is_elevated
from shepherd_server.config import config

router = APIRouter(prefix="/testbed", tags=["Testbed"])


@router.get("")
async def testbed_info() -> Testbed:
    return Testbed(name=config.testbed_name)


@router.get("/restrictions")
async def get_restrictions() -> list[str] | None:
    tb_ = await TestbedDB.get_one()
    return tb_.restrictions


@router.patch("/restrictions", dependencies=[Depends(active_user_is_admin)])
async def set_restrictions(restrictions: list[str]) -> Response:
    tb_ = await TestbedDB.get_one()
    tb_.restrictions = restrictions
    tb_.save_changes()
    return Response(status_code=200, content="Command successful executed")


herd_cmds = {"restart", "resync", "inventorize", "stop-measurement", "min-space"}
server_cmds = {"start-scheduler", "stop-scheduler"}


@router.get("/command", dependencies=[Depends(active_user_is_elevated)])
async def get_command() -> list[str]:
    return list(herd_cmds | server_cmds)


def run_command_noasync(cmd: str) -> Response:
    # TODO: add forced sysrqd-reboot
    # TODO: get deeper stats (space, ram, cpu)
    #       /usr/bin/df --type=ext4 --local --output=avail
    # TODO: add cleanup for sheep (rotate logs, clean caches, ?)
    cmd = cmd.lower().strip()
    if cmd in herd_cmds:
        with Herd() as herd:
            if cmd == "restart":
                ret = herd.reboot()
            elif cmd == "resync":
                ret = herd.resync()
            elif cmd == "inventorize":
                ret = herd.inventorize(output_path=Path("/var/shepherd"))  # TODO: load and output
            elif cmd == "stop-measurement":
                ret = herd.stop_measurement()
            elif cmd == "min-space":
                ret = herd.min_space_left()
                return Response(status_code=200, content=str(ret))
            else:
                return Response(status_code=404, content="Herd-Command not implemented")
    elif cmd in server_cmds:
        ret = subprocess.run(  # noqa: S603,
            [
                "/usr/bin/sudo",
                "/usr/bin/systemctl",
                cmd.split("-")[0],
                "shepherd-scheduler.service",
            ],
            capture_output=False,
            timeout=20,
            check=False,
        ).returncode
    else:
        return Response(status_code=404, content="Invalid command")

    if ret in [0, False]:
        return Response(status_code=200, content="Command successful executed")
    return Response(status_code=400, content="Command failed on at least one Host")


@router.patch("/command", dependencies=[Depends(active_user_is_elevated)])
async def run_command(cmd: str) -> Response:
    return await asyncio.to_thread(run_command_noasync, cmd)
