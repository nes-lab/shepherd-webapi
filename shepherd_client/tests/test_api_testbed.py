import time

import pytest
from shepherd_client.client_user import UserClient

from shepherd_client import AdminClient
from shepherd_client import TestbedClient

# ###############################################################################
# Status
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_testbed_status_fails(testbed_client: TestbedClient) -> None:
    state = testbed_client.testbed_status()
    assert not state


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
@pytest.mark.usefixtures("_server_scheduler_up")
@pytest.mark.timeout(30)
@pytest.mark.skip(reason="scheduler runs in drymode")
def test_testbed_status_with_scheduler(testbed_client: TestbedClient) -> None:
    state = False
    while not state:
        time.sleep(1)  # dynamically retry
        state = testbed_client.testbed_status(allow_dry_run=True)
        # TODO: next version allows excusing dry-mode!
    assert state


# ###############################################################################
# Name
# ###############################################################################


@pytest.mark.usefixtures("_server_api_up")
@pytest.mark.usefixtures("_server_scheduler_up")
def test_testbed_name(testbed_client: TestbedClient) -> None:
    name = testbed_client.testbed_name()
    assert isinstance(name, str)
    assert len(name) > 1
    assert name == "unit_testing_testbed"


# ###############################################################################
# Restrictions
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_admin_adds_restrictions(user1_client: UserClient, admin_client: AdminClient) -> None:
    data = user1_client.testbed_restrictions()
    assert len(data) == 0
    success = admin_client.set_restrictions(["something is up"])
    assert success
    data = user1_client.testbed_restrictions()
    assert len(data) > 0


@pytest.mark.usefixtures("_server_api_up")
def test_admin_removes_restrictions(user1_client: UserClient, admin_client: AdminClient) -> None:
    success = admin_client.set_restrictions([])
    assert success
    data = user1_client.testbed_restrictions()
    assert len(data) == 0
