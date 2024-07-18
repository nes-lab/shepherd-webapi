from contextlib import contextmanager
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from shepherd_wsrv.api_experiment.models import WebExperiment
from shepherd_wsrv.api_instance import app
from shepherd_wsrv.api_user.models import User
from shepherd_wsrv.api_user.utils_mail import MailEngine
from shepherd_wsrv.api_user.utils_mail import mail_engine
from shepherd_wsrv.api_user.utils_misc import calculate_password_hash
from shepherd_wsrv.db_instance import db_client


@pytest_asyncio.fixture
async def database_for_tests():
    await db_client()

    await User.delete_all()
    await WebExperiment.delete_all()

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

    admin_user = user.model_copy(deep=True)
    admin_user.email = "admin@test.com"
    admin_user.role = "admin"
    await User.insert_one(admin_user)

    unconfirmed_user = user.model_copy(deep=True)
    unconfirmed_user.email = "unconfirmed_mail@test.com"
    unconfirmed_user.email_confirmed_at = None
    await User.insert_one(unconfirmed_user)

    disabled_user = user.model_copy(deep=True)
    disabled_user.email = "disabled@test.com"
    disabled_user.disabled = True
    await User.insert_one(disabled_user)


class UserTestClient(TestClient):
    @contextmanager
    def authenticate_admin(self):
        response = self.post(
            "/auth/token",
            data={
                "username": "admin@test.com",
                "password": "password",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        self.headers["Authorization"] = f"Bearer {response.json()["access_token"]}"
        yield self
        self.headers["Authorization"] = ""

    @contextmanager
    def authenticate_user(self):
        response = self.post(
            "/auth/token",
            data={
                "username": "user@test.com",
                "password": "password",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        self.headers["Authorization"] = f"Bearer {response.json()["access_token"]}"
        yield self
        self.headers["Authorization"] = ""


@pytest.fixture
def client(database_for_tests: None):
    with UserTestClient(app) as client:
        yield client


@pytest.fixture
def authenticated_client(client: UserTestClient):
    with client.authenticate_user():
        yield client


@pytest.fixture
def authenticated_admin_client(client: UserTestClient):
    with client.authenticate_admin():
        yield client


class MockMailEngine(MailEngine):
    def __init__(self):
        self.send_verification_email = AsyncMock()
        self.send_password_reset_email = AsyncMock()


@pytest.fixture
def mail_engine_mock():
    mock = MockMailEngine()
    app.dependency_overrides[mail_engine] = lambda: mock
    return mock
