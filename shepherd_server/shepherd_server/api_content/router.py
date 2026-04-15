from fastapi import APIRouter
from fastapi import HTTPException
from shepherd_core.data_models.base.content import ContentModel
from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware
from shepherd_core.data_models.content import VirtualHarvesterConfig
from shepherd_core.data_models.content import VirtualSourceConfig
from shepherd_core.data_models.content import VirtualStorageConfig
from shepherd_core.testbed_client import tb_client

router = APIRouter(prefix="/content", tags=["Content"])

content_types = [
    EnergyEnvironment,
    VirtualHarvesterConfig,
    VirtualSourceConfig,
    VirtualStorageConfig,
    Firmware,
]
content_names = [content.__name__ for content in content_types]

tb_client.fixture_cache.complete_fixtures()


@router.get("")
async def list_content_types() -> list[str]:
    return sorted(content_names)


@router.get("/{content}")
async def list_content_by_type(content: str) -> list[str]:
    if content not in content_names:
        raise HTTPException(404, "Not Found")
    data = tb_client.query_ids(content)
    models = [tb_client.query_item(content, uid=uid) for uid in data]
    models = [model for model in models if model.get("deprecated") is None]
    models = [model for model in models if model.get("visible2all")]  # TODO: or user identical
    return sorted([model.get("name") for model in models])
    # -> moved from sorted dict[ID,name] (that was resorted by fastapi) to just list of names
    # TODO: replace fixture-endpoints by database-endpoints
    # TODO: include user/group-data

    # TODO: add setter-endpoint
    # TODO: add modifiers-endpoint


@router.get("/{content}/{name}")
async def get_content_by_type_and_name(content: str, name: str) -> ContentModel:
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
