import asyncio

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from shepherd_server.api_accounts.utils_mail import MailEngine
from shepherd_server.instance_db import db_create_admin

from .conftest import UserTestClient


def test_create_admin_invalid_mail() -> None:
    with pytest.raises(ValidationError):
        asyncio.run(db_create_admin("padmin", "1234567890"))


def test_create_admin_invalid_password() -> None:
    with pytest.raises(ValidationError):
        asyncio.run(db_create_admin("padmin2@cadmin.de", "123"))


@pytest.mark.skip  # TODO: fix mock.problem - create_admin() sends real mail
def test_unverified_admin_cannot_login(
    client: UserTestClient,
    mail_engine_mock: MailEngine,
) -> None:
    # with mock.patch("shepherd_server.api_accounts.utils_mail.FastMailEngine", new=MockMailEngine):
    asyncio.run(db_create_admin("padmin2@cadmin.de", "1234567890"))
    # mail_engine_mock.send_verification_email("hasn@kanns", "ods")
    mail_engine_mock.send_verification_email.assert_called_once()

    with client.regular_joe():
        login_response = client.post(
            "/auth/token",
            data={
                "username": "padmin2@cadmin.de",
                "password": "1234567890",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_response.status_code >= 400


@pytest.mark.skip  # TODO: fix mock.problem - create_admin() sends real mail
def test_verified_admin_can_login(
    client: TestClient,
    mail_engine_mock: MailEngine,
) -> None:
    from shepherd_server.instance_db import db_create_admin

    asyncio.run(db_create_admin("padmin3@cadmin.de", "1234567890"))
    mail_engine_mock.send_verification_email.assert_called_once()
    _, token = mail_engine_mock.send_verification_email.call_args.args

    verification_response = client.post(
        f"/accounts/verify/{token}",
    )
    assert verification_response.status_code == 200

    login_response = client.post(
        "/auth/token",
        data={
            "username": "padmin3@cadmin.de",
            "password": "1234567890",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200


@pytest.mark.skip
def test_create_admin_and_login() -> None:
    pass
