from fastapi.testclient import TestClient

from shepherd_server.api_user.utils_mail import MailEngine
from shepherd_server.api_user.utils_misc import calculate_hash
from tests.conftest import UserTestClient


def test_user_approves_registration_rejected(client: UserTestClient) -> None:
    with client.authenticate_user():
        rsp = client.post(
            url="/user/approve",
            json={"email": "some_new_user@test.com"},
        )
        assert rsp.status_code >= 400


def test_admin_approves_registration(
    client: UserTestClient,
    mail_engine_mock: MailEngine,
) -> None:
    with client.authenticate_admin():
        rsp = client.post(
            url="/user/approve",
            json={"email": "some_new_user@test.com"},
        )
        assert rsp.status_code == 200
    mail_engine_mock.send_approval_email.assert_called_once()
    _, token1 = mail_engine_mock.send_approval_email.call_args.args
    token2 = rsp.content.decode()
    assert token1 == token2


def test_register_user_without_token(client: TestClient) -> None:
    response = client.post(
        "/user/register",
        json={
            "email": "new@test.com",
            "password": "new_looong_pw",
        },
    )
    assert response.status_code == 422


def test_register_user_with_invalid_token(client: TestClient) -> None:
    response = client.post(
        "/user/register",
        json={
            "email": "new@test.com",
            "password": "new_looong_pw",
            "token": "123456",
        },
    )
    assert response.status_code == 404


def test_register_user_sends_mail(
    client: UserTestClient,
    mail_engine_mock: MailEngine,
) -> None:
    with client.authenticate_admin():
        rsp = client.post(
            url="/user/approve",
            json={"email": "new@test.com"},
        )
        assert rsp.status_code == 200
        mail_engine_mock.send_approval_email.assert_called_once()
    _, token = mail_engine_mock.send_approval_email.call_args.args

    with client.regular_joe():
        response = client.post(
            "/user/register",
            json={"email": "new@test.com", "password": "new_looong_pw", "token": token},
        )
        assert response.status_code == 200
        mail_engine_mock.send_registration_complete_email.assert_called_once()


def test_register_user_rejects_existing_account(
    client: TestClient,
    mail_engine_mock: MailEngine,
) -> None:
    response = client.post(
        "/user/register",
        json={
            "email": "user@test.com",
            "password": "new_looong_pw",
            "token": calculate_hash("user@test.com")[-12:],
        },
    )
    assert response.status_code == 409
    mail_engine_mock.send_verification_email.assert_not_called()


def test_register_user_rejects_short_pw(
    client: TestClient,
) -> None:
    response = client.post(
        "/user/register",
        json={
            "email": "short@test.com",
            "password": "short_pw",
            "token": calculate_hash("short@test.com")[-12:],
        },
    )
    assert response.status_code != 200
