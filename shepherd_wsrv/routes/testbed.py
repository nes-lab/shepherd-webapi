from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from shepherd_core import tb_client
from shepherd_core.data_models import Wrapper
from shepherd_core.data_models import content as shp_cnt
from shepherd_core.data_models import testbed as shp_tb

from shepherd_wsrv.api_user.utils_misc import current_active_user

router = APIRouter(
    prefix="/shepherd",
    tags=["Testbed"],
    dependencies=[Depends(current_active_user)],
)


# white-list for data-models
# TODO: implement a generator -> nicer documentation needed
name2model = {
    # testbed-components
    "Cape": shp_tb.Cape,
    "GPIO": shp_tb.GPIO,
    "MCU": shp_tb.MCU,
    "Observer": shp_tb.Observer,
    "Target": shp_tb.Target,
    "Testbed": shp_tb.Testbed,
    # content
    "EnergyEnvironment": shp_cnt.EnergyEnvironment,
    "Firmware": shp_cnt.Firmware,
    "VirtualHarvesterConfig": shp_cnt.VirtualHarvesterConfig,
    "VirtualSourceConfig": shp_cnt.VirtualSourceConfig,
}


@router.get("/{type_name}/ids")  # items?skip=10&limit=100
async def read_item_ids_list(type_name: str, skip: int = 0, limit: int = 40) -> dict:
    if type_name not in name2model:
        raise HTTPException(status_code=404, detail="item-name not found")
    elems = tb_client.query_ids(type_name)
    return {"message": elems[skip : skip + limit]}


@router.get("/{type_name}/names")  # items?skip=10&limit=100
async def read_item_names_list(type_name: str, skip: int = 0, limit: int = 40) -> dict:
    if type_name not in name2model:
        raise HTTPException(status_code=404, detail="item-name not found")
    elems = tb_client.query_names(type_name)
    return {"message": list(elems)[skip : skip + limit]}


@router.get("/{type_name}/item")
async def read_item_by_id(
    type_name: str,
    item_id: int | None = None,
    item_name: str | None = None,
) -> dict:
    if type_name not in name2model:
        raise HTTPException(status_code=404, detail="item-name not found")

    if item_id:
        try:
            return name2model[type_name](id=item_id).dict()
        except ValueError:
            raise HTTPException(status_code=404, detail="item-id not found") from None

    elif item_name:
        try:
            return name2model[type_name](name=item_name).dict()
        except ValueError:
            raise HTTPException(status_code=404, detail="item-name not found") from None

    raise HTTPException(status_code=404, detail="neither item-id or -name provided")


@router.post("/{type_name}/add")
async def write_item(type_name: str, item: Wrapper) -> None:
    pass
