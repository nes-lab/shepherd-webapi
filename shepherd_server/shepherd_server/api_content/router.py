from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from shepherd_core.data_models import ContentModel
from shepherd_core.data_models import EnergyEnvironment
from shepherd_core.data_models import VirtualHarvesterConfig
from shepherd_core.data_models import VirtualSourceConfig
from shepherd_core.testbed_client import tb_client

router = APIRouter(prefix="/content", tags=["Content"])

# TODO: add virtual_storage
content_types = [EnergyEnvironment, VirtualHarvesterConfig, VirtualSourceConfig]
content_names = [content.__name__ for content in content_types]


@router.get("")
async def list_content_types() -> list[str]:
    return sorted(content_names)


@router.get("/{content}")
async def list_content_by_type(content: str) -> JSONResponse:
    if content not in content_names:
        raise HTTPException(404, "Not Found")
    data = tb_client.query_ids(content)
    data = {uid: tb_client.query_item(content, uid=uid).get("name") for uid in data}
    return JSONResponse(content=jsonable_encoder(sorted(data.items())))
    # TODO: replace fixture-endpoints by database-endpoints
    # TODO: include user/group-data
    # TODO: add setters
    # TODO: add modifiers
    # TODO: returning a dict removes order-by-value (now by key)


@router.get("/{content}/{name}")
async def get_content_by_type(content: str, name: str) -> ContentModel:
    if content not in content_names:
        raise HTTPException(404, "Not Found")
    try:
        data = tb_client.query_item(content, name=name)
    except ValueError:
        data = None
    if name.isdecimal() and int(name) in tb_client.query_ids(content):
        data = tb_client.query_item(content, uid=int(name))
    if data is None:
        raise HTTPException(404, "Not Found")
    return content_types[content_names.index(content)](**data)
