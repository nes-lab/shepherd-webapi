from fastapi.testclient import TestClient


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
    assert response.status_code == 401


def test_login_rejects_non_existing_user(client: TestClient):
    response = client.post(
        "/auth/token",
        data={
            "username": "non-existing@test.com",
            "password": "wrong-password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401


def test_login_rejects_if_mail_is_unconfirmed(client: TestClient):
    response = client.post(
        "/auth/token",
        data={
            "username": "unconfirmed_mail@test.com",
            "password": "password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401


def test_login_rejects_disabled_user(client: TestClient):
    response = client.post(
        "/auth/token",
        data={
            "username": "disabled@test.com",
            "password": "password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401
