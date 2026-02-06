from datetime import datetime
from datetime import timedelta
from pathlib import Path

import pytest
import shepherd_core.data_models as sdm
from fastapi.testclient import TestClient
from shepherd_core import local_tz
from shepherd_core.data_models.testbed import MCU
from shepherd_server.api_user.models import UserQuota
from shepherd_server.config import config

from .conftest import UserTestClient


def test_create_experiment_is_authenticated(client: TestClient) -> None:
    response = client.post("/experiment")
    assert response.status_code == 401


@pytest.mark.dependency
def test_create_experiment_succeeds(
    client: UserTestClient,
    sample_experiment: sdm.Experiment,
) -> None:
    with client.authenticate_user_1():
        response = client.post(
            "/experiment",
            data=sample_experiment.model_dump_json(),
        )
        assert response.status_code == 200


@pytest.mark.dependency
def test_create_experiment_as_admin_succeeds(
    client: UserTestClient,
    sample_experiment: sdm.Experiment,
) -> None:
    with client.authenticate_admin():
        response = client.get("/experiment")
        assert response.status_code == 200
        assert len(response.json()) == 0

        response = client.post(
            "/experiment",
            data=sample_experiment.model_dump_json(),
        )
        assert response.status_code == 200

        response = client.get("/experiment")
        assert response.status_code == 200
        assert len(response.json()) == 1


def test_create_experiment_needs_duration(
    client: UserTestClient,
    sample_target_config: sdm.TargetConfig,
) -> None:
    _xp = sdm.Experiment(
        name="test-experiment",
        target_configs=[sample_target_config],
    )
    with client.authenticate_user_1():
        response = client.post(
            "/experiment",
            data=_xp.model_dump_json(),
        )
        assert response.status_code >= 400


def test_create_experiment_duration_has_quota(
    client: UserTestClient,
    sample_target_config: sdm.TargetConfig,
) -> None:
    _xp = sdm.Experiment(
        name="test-experiment",
        duration=config.quota_default_duration + timedelta(seconds=5),
        target_configs=[sample_target_config],
    )
    with client.authenticate_user_1():
        response = client.post(
            "/experiment",
            data=_xp.model_dump_json(),
        )
        assert response.status_code >= 400


def test_create_experiment_duration_with_expired_quota(
    client: UserTestClient,
    sample_target_config: sdm.TargetConfig,
) -> None:
    with client.authenticate_admin():
        json_dict = {
            "email": "user@test.com",
            "quota": UserQuota(
                custom_quota_expire_date=datetime.now(tz=local_tz()) - timedelta(minutes=5),
                custom_quota_duration=timedelta(hours=60),
            ).model_dump(exclude_defaults=True, mode="json"),
        }
        response = client.patch("/user/quota", json=json_dict)
        assert response.status_code == 200

    with client.authenticate_user_1():
        _xp = sdm.Experiment(
            name="test-experiment",
            duration=config.quota_default_duration + timedelta(seconds=5),
            target_configs=[sample_target_config],
        )
        response = client.post(
            "/experiment",
            data=_xp.model_dump_json(exclude_defaults=True),
        )
        assert response.status_code >= 400


def test_create_experiment_duration_with_valid_quota(
    client: UserTestClient,
    sample_target_config: sdm.TargetConfig,
) -> None:
    with client.authenticate_admin():
        json_dict = {
            "email": "user@test.com",
            "quota": UserQuota(
                custom_quota_expire_date=datetime.now(tz=local_tz()) + timedelta(minutes=5),
                custom_quota_duration=timedelta(hours=60),
            ).model_dump(exclude_defaults=True, mode="json"),
        }
        response = client.patch("/user/quota", json=json_dict)
        assert response.status_code == 200

    with client.authenticate_user_1():
        xp = sdm.Experiment(
            name="test-experiment",
            duration=config.quota_default_duration + timedelta(seconds=5),
            target_configs=[sample_target_config],
        )
        response = client.post(
            "/experiment",
            data=xp.model_dump_json(exclude_defaults=True),
        )
        assert response.status_code == 200


def test_create_experiment_only_fifo_scheduler(
    client: UserTestClient,
    sample_target_config: sdm.TargetConfig,
) -> None:
    xp = sdm.Experiment(
        name="test-experiment",
        time_start=datetime.now(tz=local_tz()) + timedelta(minutes=1),
        duration=30,
        target_configs=[sample_target_config],
    )
    with client.authenticate_user_1():
        response = client.post(
            "/experiment",
            data=xp.model_dump_json(),
        )
        assert response.status_code >= 400


def test_create_experiment_with_unconstrained_path(
    client: UserTestClient,
) -> None:
    target_config = sdm.TargetConfig(
        target_IDs=[42],
        energy_env=sdm.EnergyEnvironment(name="synthetic_static_3000mV_50mA"),
        firmware1=sdm.Firmware(
            name="FW_TestXYZ",
            data=Path("/etc/shepherd/private_data.elf"),
            data_type=sdm.FirmwareDType.path_elf,
            data_local=True,
            mcu=MCU(name="nRF52"),
        ),
        power_tracing=None,
        uart_logging=sdm.UartLogging(baudrate=115_200),
        gpio_tracing=sdm.GpioTracing(),
    )
    xp = sdm.Experiment(
        name="breaching-experiment",
        duration=30,
        target_configs=[target_config],
    )
    with client.authenticate_user_1():
        response = client.post(
            "/experiment",
            data=xp.model_dump_json(),
        )
        print(response.status_code)
        print(response.json())
        # TODO: old .is_contained is faulty, so this won't trigger for now
        assert response.status_code >= 4000  # expect 403


def test_list_experiments_is_authenticated(client: TestClient) -> None:
    response = client.get("/experiment")
    assert response.status_code == 401


@pytest.mark.dependency
def test_list_experiments(
    client: UserTestClient,
    created_experiment_id: str,
) -> None:
    with client.authenticate_user_1():
        response = client.get("/experiment")
    assert response.status_code == 200
    assert len(response.json()) == 4
    assert response.json()[created_experiment_id] is not None
    assert response.json()[created_experiment_id] == "created"


def test_experiments_are_private_to_user(
    client: UserTestClient,
    sample_experiment: sdm.Experiment,
) -> None:
    with client.authenticate_user_1():
        response = client.get("/experiment")
        assert response.status_code == 200
        assert len(response.json()) == 3

    with client.authenticate_admin():
        response = client.get("/experiment")
        assert response.status_code == 200
        assert len(response.json()) == 0

        response = client.post(
            "/experiment",
            data=sample_experiment.model_dump_json(),
        )
        assert response.status_code == 200

    with client.authenticate_user_1():
        response = client.get("/experiment")
        assert response.status_code == 200
        assert len(response.json()) == 3


@pytest.fixture
def created_experiment_id(
    client: UserTestClient,
    sample_experiment: sdm.Experiment,
) -> str:
    with client.authenticate_user_1():
        response = client.post(
            "/experiment",
            data=sample_experiment.model_dump_json(),
        )
    assert response.status_code == 200
    return response.json()


@pytest.mark.dependency(depends=["test_create_experiment_succeeds", "test_list_experiments"])
def test_get_experiment_by_id(
    client: UserTestClient,
    created_experiment_id: str,
) -> None:
    with client.authenticate_user_1():
        response = client.get(f"/experiment/{created_experiment_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "test-experiment"


def test_get_experiment_returns_not_found_for_invalid_id(
    client: UserTestClient,
) -> None:
    with client.authenticate_user_1():
        response = client.get("/experiment/ab89cb3f-50c1-402a-aa28-078697387029")
    assert response.status_code == 404


def test_get_experiment_is_authenticated(client: UserTestClient) -> None:
    response = client.get("/experiment/ab89cb3f-50c1-402a-aa28-078697387029")
    assert response.status_code == 401


@pytest.mark.dependency(depends=["test_create_experiment_succeeds", "test_list_experiments"])
def test_get_experiment_is_private_to_user(
    client: UserTestClient,
    sample_experiment: sdm.Experiment,
) -> None:
    with client.authenticate_user_1():
        client.post(
            "/experiment",
            data=sample_experiment.model_dump_json(),
        )
        response = client.get("/experiment")
        experiment_id = next(iter(response.json().keys()))
        response = client.get(f"/experiment/{experiment_id}")
        assert response.status_code == 200

    with client.authenticate_user_2():
        response = client.get(f"/experiment/{experiment_id}")
        assert response.status_code >= 400

    with client.authenticate_admin():
        response = client.get(f"/experiment/{experiment_id}")
        assert response.status_code >= 400


@pytest.mark.dependency(depends=["test_create_experiment_succeeds"])
def test_get_all_experiments_is_admin_only(
    client: UserTestClient,
) -> None:
    with client.authenticate_user_1():
        response = client.get("/experiment/all")
        assert response.status_code == 403

    with client.authenticate_admin():
        # Admins are allowed
        response = client.get("/experiment/all")
        assert response.status_code == 200


@pytest.mark.dependency(depends=["test_create_experiment_succeeds", "test_list_experiments"])
def test_get_all_experiments_shows_all(
    client: UserTestClient,
    sample_experiment: sdm.Experiment,
) -> None:
    with client.authenticate_user_1():
        client.post(
            "/experiment",
            data=sample_experiment.model_dump_json(),
        )

    with client.authenticate_user_1():
        response = client.get("/experiment")
        len_u1 = len(response.json().keys())

    with client.authenticate_user_2():
        response = client.get("/experiment")
        len_u2 = len(response.json().keys())

    with client.authenticate_admin():
        response = client.get("/experiment")
        len_a1 = len(response.json().keys())
        response = client.get("/experiment/all")
        len_a2 = len(response.json().keys())

    print(f"user1={len_u1}, user2={len_u2}, admin={len_a1}, all={len_a2}")

    assert len_u1 > len_u2
    assert len_u1 > len_a1
    assert len_a2 > len_a1
    assert len_a2 >= len_u1


# TODO: schedule idempotency


def test_schedule_experiment(client: UserTestClient, created_experiment_id: str) -> None:
    with client.authenticate_user_1():
        response = client.post(f"/experiment/{created_experiment_id}/schedule")
        assert response.status_code == 204
        response = client.get(f"/experiment/{created_experiment_id}/state")
        assert response.json() == "scheduled"


# TODO: schedule when quota is full - 3 kinds


def test_state_of_fresh_experiments(client: UserTestClient, created_experiment_id: str) -> None:
    with client.authenticate_user_1():
        response = client.get(f"/experiment/{created_experiment_id}/state")
    assert response.status_code == 200
    assert response.json() == "created"


def test_experiment_state_not_found(
    client: UserTestClient,
) -> None:
    with client.authenticate_user_1():
        response = client.get("/experiment/ab89cb3f-50c1-402a-aa28-078697387029/state")
    assert response.status_code == 404


def test_experiment_state_requires_authentication(client: UserTestClient) -> None:
    response = client.get("/experiment/ab89cb3f-50c1-402a-aa28-078697387029")
    assert response.status_code == 401


def test_experiment_state_is_private_to_owner(
    client: UserTestClient,
    sample_experiment: sdm.Experiment,
) -> None:
    with client.authenticate_user_1():
        client.post(
            "/experiment",
            data=sample_experiment.model_dump_json(),
        )
        response = client.get("/experiment")
        experiment_id = next(iter(response.json().keys()))
        response = client.get(f"/experiment/{experiment_id}/state")
        assert response.status_code == 200

    with client.authenticate_user_2():
        response = client.get(f"/experiment/{experiment_id}/state")
        assert response.status_code == 403

    with client.authenticate_admin():
        response = client.get(f"/experiment/{experiment_id}/state")
        assert response.status_code == 200


def test_experiment_statistics_is_private_to_owner(
    client: UserTestClient,
    sample_experiment: sdm.Experiment,
) -> None:
    with client.authenticate_user_1():
        client.post(
            "/experiment",
            data=sample_experiment.model_dump_json(),
        )
        response = client.get("/experiment")
        experiment_id = next(iter(response.json().keys()))
        response = client.get(f"/experiment/{experiment_id}/statistics")
        assert response.status_code == 200

    with client.authenticate_user_2():
        response = client.get(f"/experiment/{experiment_id}/statistics")
        assert response.status_code >= 400

    with client.authenticate_admin():
        response = client.get(f"/experiment/{experiment_id}/statistics")
        assert response.status_code == 200


def test_experiment_state_scheduled(client: UserTestClient, scheduled_experiment_id: str) -> None:
    with client.authenticate_user_1():
        response = client.get(f"/experiment/{scheduled_experiment_id}/state")
    assert response.status_code == 200
    assert response.json() == "scheduled"


def test_experiment_state_running(client: UserTestClient, running_experiment_id: str) -> None:
    with client.authenticate_user_1():
        response = client.get(f"/experiment/{running_experiment_id}/state")
    assert response.status_code == 200
    assert response.json() == "running"


def test_experiment_state_finished(client: UserTestClient, finished_experiment_id: str) -> None:
    with client.authenticate_user_1():
        response = client.get(f"/experiment/{finished_experiment_id}/state")
    assert response.status_code == 200
    assert response.json() == "finished"


def test_download_rejected_for_unfinished_experiments(
    client: UserTestClient, scheduled_experiment_id: str, running_experiment_id: str
) -> None:
    with client.authenticate_user_1():
        response = client.get(f"/experiment/{scheduled_experiment_id}/download")
        assert response.status_code == 409

        response = client.get(f"/experiment/{running_experiment_id}/download")
        assert response.status_code == 409


def test_download_lists_sheep_files(client: UserTestClient, finished_experiment_id: str) -> None:
    with client.authenticate_user_1():
        response = client.get(f"/experiment/{finished_experiment_id}/download")
    assert response.status_code == 200
    assert response.json() == ["unit_testing_sheep"]


def test_download_rejects_incorrect_sheeps(
    client: UserTestClient, finished_experiment_id: str
) -> None:
    with client.authenticate_user_1():
        response = client.get(f"/experiment/{finished_experiment_id}/download/invalid_sheep")
    assert response.status_code == 404


def test_download_sheep_sends_file(client: UserTestClient, finished_experiment_id: str) -> None:
    with client.authenticate_user_1():
        response = client.get(f"/experiment/{finished_experiment_id}/download/unit_testing_sheep")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-hdf5"
    assert int(response.headers["content-length"]) > 100
