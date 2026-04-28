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

resource_types = [
    # content
    EnergyEnvironment,
    VirtualHarvesterConfig,
    VirtualSourceConfig,
    VirtualStorageConfig,
    Firmware,
    # tb-components
    Cape,
    GPIO,
    MCU,
    Observer,
    Target,
    Testbed,
]
resource_names = [content.__name__.lower() for content in resource_types]


@router.get("")
async def list_content_types() -> list[str]:
    return sorted(resource.__name__ for resource in resource_types)


@router.get("/{resource}")
async def list_resource_by_type(resource: str) -> dict[int, str]:
    resource = resource.lower()
    if resource not in resource_names:
        raise HTTPException(404, "Not Found")
    data = tb_client.list_resource_names(resource)
    models = [tb_client.get_resource_item(resource, name=name) for name in data]
    models = [model for model in models if model.get("deprecated") is None]
    models = [
        model for model in models if model.get("visible2all", True)
    ]  # TODO: or account identical
    return {int(model.get("id", 0)): str(model.get("name")) for model in models}
    # -> moved from sorted dict[ID,name] (that was resorted by fastapi) to
    #      - just list of names (was hardly usable by TestbedClient)
    #      - unsorted dict[ID, name]
    # TODO: replace fixture-endpoints by database-endpoints
    # TODO: include data of account/group

    # TODO: add setter-endpoint
    # TODO: add modifiers-endpoint


@router.get("/{resource}/{name}")
async def get_resource_by_type_and_name(resource: str, name: str) -> ContentModel:
    resource = resource.lower()
    if resource not in resource_names:
        raise HTTPException(404, "Not Found")
    try:
        data = tb_client.get_resource_item(resource, name=name)
    except ValueError:
        data = None
    if name.isdecimal() and int(name) in tb_client.list_resource_ids(resource):
        data = tb_client.get_resource_item(resource, uid=int(name))
    if data is None:
        raise HTTPException(404, "Not Found")
    return resource_types[resource_names.index(resource)](**data)
