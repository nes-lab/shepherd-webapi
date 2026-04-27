import time
from datetime import timedelta

import pytest
from shepherd_client.client_user import UserClient
from shepherd_core import local_now
from shepherd_core.data_models import Experiment
from shepherd_server.api_accounts.utils_misc import calculate_hash

from shepherd_client import AdminClient

# ###############################################################################
# AUTH
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_registering_new_account_without_approval_is_rejected(unknown_client: UserClient) -> None:
    success = unknown_client.authenticate()
    assert not success
    token = calculate_hash("unknown_mail@test.com")[-12:]
    success = unknown_client.register_account(token)
    assert not success
    success = unknown_client.authenticate()
    assert not success


@pytest.mark.usefixtures("_server_api_up")
def test_admin_approves_new_account(admin_client: AdminClient, unknown_client: UserClient) -> None:
    success = unknown_client.authenticate()
    assert not success
    token = admin_client.approve_account("unknown_mail@test.com")
    assert token
    success = unknown_client.register_account(token)
    assert success
    success = unknown_client.authenticate()
    assert success


# ###############################################################################
# Change account state
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_admin_activate_deactivated_account(
    deactivated_client: UserClient, admin_client: AdminClient, sample_experiment: Experiment
) -> None:
    success = deactivated_client.create_experiment(sample_experiment)
    assert not success
    success = admin_client.change_account_state("deactivated_mail@test.com", enabled=True)
    assert success
    success = deactivated_client.create_experiment(sample_experiment)
    assert success


@pytest.mark.usefixtures("_server_api_up")
def test_admin_deactivate_active_account(
    user1_client: UserClient, admin_client: AdminClient, sample_experiment: Experiment
) -> None:
    success = user1_client.create_experiment(sample_experiment)
    assert success
    success = admin_client.change_account_state("user@test.com", enabled=False)
    assert success
    success = user1_client.create_experiment(sample_experiment)
    assert not success


# ###############################################################################
# Change account Quota
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_admin_updated_quota_date(user1_client: UserClient, admin_client: AdminClient) -> None:
    admin_client.extend_quota(
        account_email="user@test.com",
        expire_date=local_now() + timedelta(minutes=5),
        duration=None,
        storage=None,
        force=True,
    )
    data = user1_client.get_account_info()
    assert data["custom_quota_expire_date"] is not None
    assert data["custom_quota_duration"] is None
    assert data["custom_quota_storage"] is None


@pytest.mark.usefixtures("_server_api_up")
def test_admin_updated_quota_duration(user1_client: UserClient, admin_client: AdminClient) -> None:
    admin_client.extend_quota(
        account_email="user@test.com",
        expire_date=None,
        duration=timedelta(hours=10),
        storage=None,
        force=True,
    )
    data = user1_client.get_account_info()
    assert data["custom_quota_expire_date"] is None
    assert data["custom_quota_duration"] is not None
    assert data["custom_quota_storage"] is None


@pytest.mark.usefixtures("_server_api_up")
def test_admin_updated_quota_storage(user1_client: UserClient, admin_client: AdminClient) -> None:
    admin_client.extend_quota(
        account_email="user@test.com",
        expire_date=None,
        duration=None,
        storage=500 * 10**9,
        force=True,
    )
    data = user1_client.get_account_info()
    assert data["custom_quota_expire_date"] is None
    assert data["custom_quota_duration"] is None
    assert data["custom_quota_storage"] is not None


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_admin_updated_quota_unforced(user1_client: UserClient, admin_client: AdminClient) -> None:
    admin_client.extend_quota(
        account_email="user@test.com",
        storage=500 * 10**9,
    )
    data = user1_client.get_account_info()
    assert data["custom_quota_expire_date"] is None
    assert data["custom_quota_duration"] is None
    assert data["custom_quota_storage"] is not None

    admin_client.extend_quota(
        account_email="user@test.com",
        duration=timedelta(hours=10),
    )
    data = user1_client.get_account_info()
    assert data["custom_quota_expire_date"] is None
    assert data["custom_quota_duration"] is not None
    assert data["custom_quota_storage"] is not None


# ###############################################################################
# Add restrictions
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


# ###############################################################################
# Commands
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_admin_get_commands(admin_client: AdminClient) -> None:
    data = admin_client.get_commands()
    assert len(data) > 0


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
@pytest.mark.usefixtures("_server_scheduler_up")
@pytest.mark.timeout(60)
def test_admin_send_command_space(admin_client: AdminClient) -> None:
    state = False
    while not state:
        time.sleep(1)  # dynamically retry
        state = admin_client.testbed_status()
    data = admin_client.get_commands()
    print(data)
    assert len(data) > 0
    assert "min-space" in data
    success = admin_client.send_command("min-space")
    assert success


# ###############################################################################
# List all
# ###############################################################################


@pytest.mark.usefixtures("_server_api_up")
def test_admin_list_all_experiments(admin_client: AdminClient) -> None:
    uids1 = admin_client.list_experiments()
    uids2 = admin_client.list_all_experiments()
    assert len(uids2) >= len(uids1)
    assert len(uids2) > 0


@pytest.mark.usefixtures("_server_api_up")
def test_admin_list_all_accounts(admin_client: AdminClient) -> None:
    data = admin_client.list_all_accounts()
    assert len(data) > 4
    # at least: 2 users, 1 admin, 1 unconfirmed, 1 deactivated
