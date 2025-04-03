import pytest
from fastapi.testclient import TestClient
from shepherd_core.data_models.experiment import Experiment

from shepherd_wsrv.tests.conftest import UserTestClient


def test_create_experiment_is_authenticated(client: TestClient):
    response = client.post("/experiment")
    assert response.status_code == 401


def test_create_experiment_succeeds(
    authenticated_client: TestClient,
    sample_experiment: Experiment,
):
    response = authenticated_client.post(
        "/experiment",
        data=sample_experiment.model_dump_json(),
    )
    assert response.status_code == 200


def test_list_experiments_is_authenticated(client: TestClient):
    response = client.get("/experiment")
    assert response.status_code == 401


def test_list_experiments(
    authenticated_client: TestClient,
    sample_experiment: Experiment,
    created_experiment_id: str,
):
    response = authenticated_client.get("/experiment")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[created_experiment_id] is not None
    assert response.json()[created_experiment_id]["name"] == "test-experiment"


def test_experiments_are_private_to_user(
    client: UserTestClient,
    sample_experiment: Experiment,
):
    with client.authenticate_user():
        response = client.get("/experiment")
        assert response.status_code == 200
        assert len(response.json()) == 0

    with client.authenticate_admin():
        response = client.get("/experiment")
        assert response.status_code == 200
        assert len(response.json()) == 0

        response = client.post(
            "/experiment",
            data=sample_experiment.model_dump_json(),
        )
        assert response.status_code == 200

    with client.authenticate_user():
        response = client.get("/experiment")
        assert response.status_code == 200
        assert len(response.json()) == 0


@pytest.fixture
def created_experiment_id(
    authenticated_client: TestClient,
    sample_experiment: Experiment,
):
    response = authenticated_client.post(
        "/experiment",
        data=sample_experiment.model_dump_json(),
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.dependency(depends=["test_create_experiment_succeeds", "test_list_experiments"])
def test_get_experiment_by_id(
    authenticated_client: TestClient,
    created_experiment_id: str,
):
    response = authenticated_client.get(f"/experiment/{created_experiment_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "test-experiment"


def test_get_experiment_returns_not_found_for_invalid_id(authenticated_client: UserTestClient):
    response = authenticated_client.get("/experiment/ab89cb3f-50c1-402a-aa28-078697387029")
    assert response.status_code == 404


def test_get_experiment_is_authenticated(client: UserTestClient):
    response = client.get("/experiment/ab89cb3f-50c1-402a-aa28-078697387029")
    assert response.status_code == 401


@pytest.mark.dependency(depends=["test_create_experiment_succeeds", "test_list_experiments"])
def test_get_experiment_is_private_to_user(
    client: UserTestClient,
    sample_experiment: Experiment,
):
    experiment_id = None
    with client.authenticate_user():
        client.post(
            "/experiment",
            data=sample_experiment.model_dump_json(),
        )
        response = client.get("/experiment")
        experiment_id = next(iter(response.json().keys()))

    with client.authenticate_admin():
        response = client.get(f"/experiment/{experiment_id}")
        assert response.status_code == 403


def test_schedule_experiment(client: UserTestClient, created_experiment_id: str):
    response = client.post(f"/experiment/{created_experiment_id}/schedule")
    assert response.status_code == 204
