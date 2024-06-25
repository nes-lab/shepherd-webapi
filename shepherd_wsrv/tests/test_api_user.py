from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from shepherd_wsrv.api_instance import app
from shepherd_wsrv.api_user.utils_mail import MailEngine
from shepherd_wsrv.api_user.utils_mail import mail_engine


def test_create_user_endpoint_requires_authentication(client: TestClient):
    response = client.post(
        "/user/register",
        json={
            "email": "new@test.com",
            "password": "password",
        },
    )
    assert response.status_code == 401


class MockMailEngine(MailEngine):
    def __init__(self):
        self.send_verification_email = AsyncMock()
        self.send_password_reset_email = AsyncMock()


@pytest.fixture
def mail_engine_mock():
    mock = MockMailEngine()
    app.dependency_overrides[mail_engine] = lambda: mock
    return mock


def test_unprivileged_user_cannot_create_new_users(
    authenticated_client: TestClient,
    mail_engine_mock,
):
    response = authenticated_client.post(
        "/user/register",
        json={
            "email": "new@test.com",
            "password": "password",
        },
    )
    assert response.status_code == 403


def test_user_can_query_account_data(authenticated_client: TestClient):
    response = authenticated_client.get("/user")
    assert response.status_code == 200
    assert response.json()["email"] == "user@test.com"
    assert response.json()["first_name"] == "first name"
    assert response.json()["last_name"] == "last name"


def test_user_account_data_endpoint_is_authenticated(client: TestClient):
    response = client.get("/user")
    assert response.status_code == 401
