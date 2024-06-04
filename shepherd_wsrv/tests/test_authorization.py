from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from shepherd_wsrv.api_instance import app
from shepherd_wsrv.api_user.models import User
from shepherd_wsrv.api_user.utils_misc import calculate_password_hash
from shepherd_wsrv.db_instance import db_client


@pytest.fixture
async def database_for_tests():
    await db_client()

    await User.delete_all()

    user = User(
        email="user@test.com",
        password=calculate_password_hash("password"),
        first_name="first name",
        last_name="last name",
        disabled=False,
        email_confirmed_at=datetime.now(),
    )

    working_user = user.model_copy(deep=True)
    await User.insert_one(working_user)

    unconfirmed_user = user.model_copy(deep=True)
    unconfirmed_user.email = "unconfirmed_mail@test.com"
    unconfirmed_user.email_confirmed_at = None
    await User.insert_one(unconfirmed_user)

    disabled_user = user.model_copy(deep=True)
    disabled_user.email = "disabled@test.com"
    disabled_user.disabled = True
    await User.insert_one(disabled_user)


@pytest.fixture
def client(database_for_tests):
    with TestClient(app) as client:
        yield client


def test_login_yields_access_token(client: TestClient):
    response = client.post(
        "/auth/token",
        data={
            "username": "user@test.com",
            "password": "password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"] is not None


def test_access_token_unlocks_authenticated_endpoints(client: TestClient):
    response = client.post(
        "/auth/token",
        data={
            "username": "user@test.com",
            "password": "password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    response = client.get(
        "/user",
        headers={"Authorization": f"Bearer {response.json()["access_token"]}"},
    )
    assert response.status_code == 200


def test_login_with_wrong_password_is_rejected(client: TestClient):
    response = client.post(
        "/auth/token",
        data={
            "username": "user@test.com",
            "password": "wrong-password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 400


def test_login_rejects_non_existing_user(client: TestClient):
    response = client.post(
        "/auth/token",
        data={
            "username": "non-existing@test.com",
            "password": "wrong-password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 400


def test_login_rejects_if_mail_is_unconfirmed(client: TestClient):
    response = client.post(
        "/auth/token",
        data={
            "username": "unconfirmed_mail@test.com",
            "password": "password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 400


def test_login_rejects_disabled_user(client: TestClient):
    response = client.post(
        "/auth/token",
        data={
            "username": "disabled@test.com",
            "password": "password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 400
