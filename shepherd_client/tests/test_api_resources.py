import pytest
from shepherd_core.testbed_client import tb_client

from shepherd_client import TestbedClient

# ###############################################################################
# Content & Components
# ###############################################################################

resource_types = tb_client.list_resource_types()


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
@pytest.mark.dependency
def test_list_resource_types(testbed_client: TestbedClient) -> None:
    elements = testbed_client.list_resource_types()
    assert isinstance(elements, list)
    assert len(elements) > 0
    global resource_types  # noqa: PLW0603
    resource_types = elements


@pytest.mark.usefixtures("_server_api_up")
@pytest.mark.parametrize("resource_type", resource_types)
@pytest.mark.dependency(depends=["test_list_resource_types"])
def test_list_resource_ids(testbed_client: TestbedClient, resource_type: str) -> None:
    ids = testbed_client.list_resource_ids(resource_type)
    assert isinstance(ids, list)
    assert len(ids) > 0


@pytest.mark.usefixtures("_server_api_up")
@pytest.mark.parametrize("resource_type", resource_types)
@pytest.mark.dependency(depends=["test_list_resource_types"])
def test_list_resource_names(testbed_client: TestbedClient, resource_type: str) -> None:
    names = testbed_client.list_resource_names(resource_type)
    assert isinstance(names, list)
    assert len(names) > 0


@pytest.mark.usefixtures("_server_api_up")
@pytest.mark.parametrize("resource_type", resource_types)
@pytest.mark.dependency(depends=["test_list_resource_types"])
def test_get_resource_by_id(testbed_client: TestbedClient, resource_type: str) -> None:
    ids = testbed_client.list_resource_ids(resource_type)
    assert isinstance(ids, list)
    assert len(ids) > 0
    item = testbed_client.get_resource_item(resource_type, uid=ids[0])
    assert isinstance(item, dict)


@pytest.mark.usefixtures("_server_api_up")
@pytest.mark.parametrize("resource_type", resource_types)
@pytest.mark.dependency(depends=["test_list_resource_types"])
def test_get_resource_by_name(testbed_client: TestbedClient, resource_type: str) -> None:
    names = testbed_client.list_resource_names(resource_type)
    assert isinstance(names, list)
    assert len(names) > 0
    item = testbed_client.get_resource_item(resource_type, name=names[0])
    assert isinstance(item, dict)


# TODO: how to try inheritance?
