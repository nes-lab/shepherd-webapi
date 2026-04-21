from fastapi import APIRouter
from fastapi import HTTPException
from shepherd_core.data_models.base.content import ContentModel
from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware
from shepherd_core.data_models.content import VirtualHarvesterConfig
from shepherd_core.data_models.content import VirtualSourceConfig
from shepherd_core.data_models.content import VirtualStorageConfig
from shepherd_core.data_models.testbed import GPIO
from shepherd_core.data_models.testbed import MCU
from shepherd_core.data_models.testbed import Cape
from shepherd_core.data_models.testbed import Observer
from shepherd_core.data_models.testbed import Target
from shepherd_core.data_models.testbed import Testbed
from shepherd_core.testbed_client import tb_client

router = APIRouter(prefix="/resources", tags=["Resources"])
# TODO: rename to resources

content_types = [
    EnergyEnvironment,
    VirtualHarvesterConfig,
    VirtualSourceConfig,
    VirtualStorageConfig,
    Firmware,
    # TODO: added tb-components - temp fix to replace fixture client
    Cape,
    GPIO,
    MCU,
    Observer,
    Target,
    Testbed,
]
content_names = [content.__name__.lower() for content in content_types]


@router.get("")
async def list_content_types() -> list[str]:
    return sorted(content.__name__ for content in content_types)


@router.get("/{content}")
async def list_content_by_type(content: str) -> dict[int, str]:
    content = content.lower()
    if content not in content_names:
        raise HTTPException(404, "Not Found")
    data = tb_client.list_resource_ids(content)
    models = [tb_client.get_resource_item(content, uid=uid) for uid in data]
    models = [model for model in models if model.get("deprecated") is None]
    models = [
        model for model in models if model.get("visible2all", True)
    ]  # TODO: or user identical
    return {int(model.get("id", 0)): str(model.get("name")) for model in models}
    # -> moved from sorted dict[ID,name] (that was resorted by fastapi) to
    #      - just list of names (was hardly usable by TestbedClient)
    #      - unsorted dict[ID, name]
    # TODO: replace fixture-endpoints by database-endpoints
    # TODO: include data of user/group

    # TODO: add setter-endpoint
    # TODO: add modifiers-endpoint


@router.get("/{content}/{name}")
async def get_content_by_type_and_name(content: str, name: str) -> ContentModel:
    content = content.lower()
    if content not in content_names:
        raise HTTPException(404, "Not Found")
    try:
        data = tb_client.get_resource_item(content, name=name)
    except ValueError:
        data = None
    if name.isdecimal() and int(name) in tb_client.list_resource_ids(content):
        data = tb_client.get_resource_item(content, uid=int(name))
    if data is None:
        raise HTTPException(404, "Not Found")
    return content_types[content_names.index(content)](**data)
