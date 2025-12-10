import asyncio
import subprocess
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Response
from shepherd_core.data_models.testbed import Cape
from shepherd_core.data_models.testbed import Observer
from shepherd_core.data_models.testbed import Target
from shepherd_core.data_models.testbed import Testbed
from shepherd_core.testbed_client import tb_client
from shepherd_herd import Herd

from shepherd_server.api_testbed.models_status import TestbedDB
from shepherd_server.api_user.utils_misc import active_user_is_admin
from shepherd_server.api_user.utils_misc import active_user_is_elevated
from shepherd_server.config import config

router = APIRouter(prefix="/testbed", tags=["Testbed"])


@router.get("")
async def testbed_info() -> Testbed:
    try:
        data = tb_client.query_item("Testbed", name=config.testbed_name)
    except ValueError:
        data = None
    if data is None:
        raise HTTPException(404, "Not Found")
    return Testbed(**data)


@router.get("/restrictions")
async def get_restrictions() -> list[str] | None:
    tb_ = await TestbedDB.get_one()
    return tb_.restrictions


@router.patch("/restrictions", dependencies=[Depends(active_user_is_admin)])
async def set_restrictions(value: Annotated[list[str], Body(embed=True)]) -> Response:
    tb_ = await TestbedDB.get_one()
    tb_.restrictions = value
    await tb_.save_changes()
    return Response(status_code=200, content="Command successful executed")


herd_cmds = {"restart", "resync", "inventorize", "stop-measurement", "min-space"}
server_cmds = {"start-scheduler", "stop-scheduler"}


@router.get("/command", dependencies=[Depends(active_user_is_elevated)])
async def get_command() -> list[str]:
    return list(herd_cmds | server_cmds)


def run_command_syn(cmd: str) -> Response:
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
async def run_command(value: Annotated[str, Body(embed=True)]) -> Response:
    return await asyncio.to_thread(run_command_syn, value)


# TODO: replace fixture-endpoints by database-endpoints


@router.get("/observer")
async def list_observers() -> list[int]:
    try:
        tb = Testbed(name=config.testbed_name)
        data = [obs.id for obs in tb.observers]
    except ValueError:
        data = tb_client.query_ids("Observer")
    return sorted(data)


@router.get("/observer/{uid}")
async def get_observer(uid: int) -> Observer:
    try:
        data = tb_client.query_item("Observer", uid=uid)
    except ValueError:
        data = None
    if data is None:
        raise HTTPException(404, "Not Found")
    return Observer(**data)


@router.get("/cape")
async def list_capes() -> list[int]:
    try:
        tb = Testbed(name=config.testbed_name)
        data = [obs.cape.id for obs in tb.observers if obs.cape is not None]
    except ValueError:
        data = tb_client.query_ids("Cape")
    return sorted(data)


@router.get("/cape/{uid}")
async def get_cape(uid: int) -> Cape:
    try:
        data = tb_client.query_item("Cape", uid=uid)
    except ValueError:
        data = None
    if data is None:
        raise HTTPException(404, "Not Found")
    return Cape(**data)


@router.get("/target")
async def list_targets() -> list[int]:
    try:
        tb = Testbed(name=config.testbed_name)
        tgt_all = tb_client.query_ids("Target")
    except ValueError:
        return []
    data = []
    for uid in tgt_all:
        try:
            if tb.get_observer(uid):
                data.append(uid)
        except ValueError:
            pass
    return sorted(data)


@router.get("/target/{uid}")
async def get_target(uid: int) -> Target:
    try:
        data = tb_client.query_item("Target", uid=uid)
    except ValueError:
        data = None
    if data is None:
        raise HTTPException(404, "Not Found")
    return Target(**data)
