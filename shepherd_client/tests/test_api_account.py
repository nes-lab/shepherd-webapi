from datetime import timedelta

import pytest
from shepherd_client.client_user import UserClient
from shepherd_core import local_now
from shepherd_server.api_accounts.models import UserOut
from shepherd_server.api_accounts.models import UserQuota

from shepherd_client import AdminClient
from tests.conftest import MockMailEngine

# ###############################################################################
# AUTH
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_authenticate_account(user1_client: UserClient) -> None:
    success = user1_client.authenticate()
    assert success


@pytest.mark.usefixtures("_server_api_up")
def test_authenticate_unconfirmed_account_is_rejected(unconfirmed_client: UserClient) -> None:
    success = unconfirmed_client.authenticate()
    assert not success
    # extra:
    success = unconfirmed_client.register_account("very-secure-token")
    assert success
    success = unconfirmed_client.authenticate()
    assert success


@pytest.mark.usefixtures("_server_api_up")
def test_authenticate_disabled_account_is_rejected(
    disabled_client: UserClient, admin_client: AdminClient
) -> None:
    success = disabled_client.authenticate()
    assert not success
    success = admin_client.change_account_state("disabled@test.com", enabled=True)
    assert success
    success = disabled_client.authenticate()
    assert success
    success = admin_client.change_account_state("disabled@test.com", enabled=False)
    assert success
    success = disabled_client.authenticate()
    assert not success


# ###############################################################################
# REGISTER
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_register_account(unconfirmed_client: UserClient) -> None:
    success = unconfirmed_client.register_account("very-secure-token")
    assert success
    success = unconfirmed_client.authenticate()
    assert success


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_register_account_with_wrong_token(unconfirmed_client: UserClient) -> None:
    success = unconfirmed_client.register_account("very-wrong-token")
    assert not success
    success = unconfirmed_client.authenticate()
    assert not success


# ###############################################################################
# INFO
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_get_account_info(user1_client: UserClient) -> None:
    response = user1_client.get_account_info()
    user = UserOut(**response)
    assert user.email == "user@test.com"
    assert user.first_name == "first name"
    assert user.last_name == "last name"


@pytest.mark.usefixtures("_server_api_up")
def test_get_account_info_is_authenticated(unconfirmed_client: UserClient) -> None:
    data = unconfirmed_client.get_account_info()
    assert len(data) == 0


@pytest.mark.usefixtures("_server_api_up")
def test_get_account_info_quota(user1_client: UserClient) -> None:
    response = user1_client.get_account_info()
    quota = UserQuota(**response)
    assert quota.custom_quota_expire_date is None
    assert quota.custom_quota_duration is None
    assert quota.custom_quota_storage is None


@pytest.mark.usefixtures("_server_api_up")
def test_get_account_info_quota_date(user1_client: UserClient, admin_client: AdminClient) -> None:
    admin_client.extend_quota(
        account="user@test.com",
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
def test_get_account_info_admin_updated_quota_duration(
    user1_client: UserClient, admin_client: AdminClient
) -> None:
    admin_client.extend_quota(
        account="user@test.com",
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
def test_get_account_info_admin_updated_quota_storage(
    user1_client: UserClient, admin_client: AdminClient
) -> None:
    admin_client.extend_quota(
        account="user@test.com",
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
def test_get_account_info_admin_updated_quota_unforced(
    user1_client: UserClient, admin_client: AdminClient
) -> None:
    admin_client.extend_quota(
        account="user@test.com",
        storage=500 * 10**9,
    )
    data = user1_client.get_account_info()
    assert data["custom_quota_expire_date"] is None
    assert data["custom_quota_duration"] is None
    assert data["custom_quota_storage"] is not None

    admin_client.extend_quota(
        account="user@test.com",
        duration=timedelta(hours=10),
    )
    data = user1_client.get_account_info()
    assert data["custom_quota_expire_date"] is None
    assert data["custom_quota_duration"] is not None
    assert data["custom_quota_storage"] is not None


# ###############################################################################
# Password reset
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_forgot_password_process(user1_client: UserClient, mail_engine: MockMailEngine) -> None:
    assert user1_client.request_password_reset()
    assert mail_engine
    # mail_engine.send_password_reset_email.assert_called_once()
    # _, token = mail_engine.send_password_reset_email.call_args.args


@pytest.mark.usefixtures("_server_api_up")
def test_forgot_password_endpoint_returns_success_for_invalid_email(
    unconfirmed_client: UserClient,
) -> None:
    assert unconfirmed_client.request_password_reset()


@pytest.mark.usefixtures("_server_api_up")
def test_reset_password_fails_without_token(unconfirmed_client: UserClient) -> None:
    assert not unconfirmed_client.reset_password(
        token="not-correct",
        password="new-password",
    )


# ###############################################################################
# Delete
# ###############################################################################
