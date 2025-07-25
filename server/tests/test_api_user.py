from datetime import datetime
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from shepherd_core import local_tz
from shepherd_server.api_user.models import UserOut
from shepherd_server.api_user.models import UserQuota
from shepherd_server.api_user.utils_mail import MailEngine

from .conftest import UserTestClient


def test_user_can_query_account_data(client: UserTestClient) -> None:
    with client.authenticate_user():
        response = client.get("/user")
    assert response.status_code == 200
    user = UserOut(**response.json())
    assert user.email == "user@test.com"
    assert user.first_name == "first name"
    assert user.last_name == "last name"


def test_user_account_data_endpoint_is_authenticated(client: TestClient) -> None:
    response = client.get("/user")
    assert response.status_code == 401


# TODO: user can update itself


@pytest.mark.dependency
def test_user_can_query_quota_data(client: UserTestClient) -> None:
    with client.authenticate_user():
        response = client.get("/user")
    assert response.status_code == 200
    quota = UserQuota(**response.json())
    assert quota.custom_quota_expire_date is None
    assert quota.custom_quota_duration is None
    assert quota.custom_quota_storage is None


@pytest.mark.dependency(depends=["test_user_can_query_quota_data"])
def test_admin_can_update_quota_date(
    client: UserTestClient,
) -> None:
    json_dict = {
        "email": "user@test.com",
        "quota": UserQuota(
            custom_quota_expire_date=datetime.now(tz=local_tz()),
        ).model_dump(exclude_defaults=True, mode="json"),
    }
    with client.authenticate_admin():
        response = client.patch("/user/quota", json=json_dict)
        assert response.status_code == 200

    with client.authenticate_user():
        response = client.get("/user")
        assert response.status_code == 200
        quota = UserQuota(**response.json())
        assert quota.custom_quota_expire_date is not None
        assert quota.custom_quota_duration is None
        assert quota.custom_quota_storage is None


@pytest.mark.dependency(depends=["test_user_can_query_quota_data"])
def test_admin_can_update_quota_duration(
    client: UserTestClient,
) -> None:
    json_dict = {
        "email": "user@test.com",
        "quota": UserQuota(
            custom_quota_duration=timedelta(hours=60),
        ).model_dump(exclude_defaults=True, mode="json"),
    }
    with client.authenticate_admin():
        response = client.patch("/user/quota", json=json_dict)
        assert response.status_code == 200

    with client.authenticate_user():
        response = client.get("/user")
        assert response.status_code == 200
        quota = UserQuota(**response.json())
        assert quota.custom_quota_expire_date is None
        assert quota.custom_quota_duration is not None
        assert quota.custom_quota_storage is None


@pytest.mark.dependency(depends=["test_user_can_query_quota_data"])
def test_admin_can_update_quota_storage(
    client: UserTestClient,
) -> None:
    json_dict = {
        "email": "user@test.com",
        "quota": UserQuota(
            custom_quota_storage=900e9,
        ).model_dump(exclude_defaults=True, mode="json"),
    }
    with client.authenticate_admin():
        response = client.patch("/user/quota", json=json_dict)
        assert response.status_code == 200

    with client.authenticate_user():
        response = client.get("/user")
        assert response.status_code == 200
        quota = UserQuota(**response.json())
        assert quota.custom_quota_expire_date is None
        assert quota.custom_quota_duration is None
        assert quota.custom_quota_storage is not None


def test_forgot_password_process(
    client: TestClient,
    mail_engine_mock: MailEngine,
) -> None:
    login_response = client.post(
        "/auth/token",
        data={
            "username": "user@test.com",
            "password": "forgotten-password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 401

    forgot_response = client.post(
        "/user/forgot-password",
        json={"email": "user@test.com"},
    )
    assert forgot_response.status_code == 200

    mail_engine_mock.send_password_reset_email.assert_called_once()
    _, token = mail_engine_mock.send_password_reset_email.call_args.args

    reset_response = client.post(
        "/user/reset-password",
        json={
            "token": token,
            "password": "some-new-password",
        },
    )
    assert reset_response.status_code == 200

    login_response = client.post(
        "/auth/token",
        data={
            "username": "user@test.com",
            "password": "some-new-password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200


def test_forgot_password_endpoint_returns_success_for_invalid_email(
    client: TestClient,
) -> None:
    response = client.post(
        "/user/forgot-password",
        json={"email": "non-existing-user@test.com"},
    )
    assert response.status_code == 200


def test_forgot_password_endpoint_returns_success_for_disabled_account(
    client: TestClient,
) -> None:
    """Regression test motivated by previously existing issue."""
    response = client.post(
        "/user/forgot-password",
        json={"email": "disabled@test.com"},
    )
    assert response.status_code == 200


def test_invalid_password_reset_token_returns_error(
    client: TestClient,
) -> None:
    response = client.post(
        "/user/reset-password",
        json={
            "token": "some-invalid-token",
            "password": "new-password",
        },
    )
    assert response.status_code == 404


def test_invalid_email_verification_token_returns_error(
    client: TestClient,
) -> None:
    response = client.post(
        "/user/verify/some-invalid-token",
    )
    assert response.status_code == 404
