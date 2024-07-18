from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from shepherd_core import fw_tools
from shepherd_core.data_models import FirmwareDType
from shepherd_core.data_models import GpioTracing
from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware
from shepherd_core.data_models.experiment import Experiment
from shepherd_core.data_models.experiment import TargetConfig
from shepherd_core.data_models.testbed import MCU

from shepherd_wsrv.tests.conftest import UserTestClient


@pytest.fixture
def sample_experiment():
    firmware_path = Path(__file__).parent / "data/test-firmware-nrf52.elf"
    return Experiment(
        name="test-experiment",
        duration=30,
        target_configs=[
            TargetConfig(
                target_IDs=[42],
                custom_IDs=[42],
                energy_env=EnergyEnvironment(name="eenv_static_3000mV_50mA_3600s"),
                firmware1=Firmware(
                    name="FW_TestXYZ",
                    data=fw_tools.file_to_base64(firmware_path),
                    data_type=FirmwareDType.base64_elf,
                    data_local=True,
                    mcu=MCU(name="nRF52"),
                ),
                power_tracing=None,
                gpio_tracing=GpioTracing(
                    uart_decode=True,
                    uart_baudrate=115_200,
                ),
            ),
        ],
    )


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
):
    response = authenticated_client.get("/experiment")
    assert response.status_code == 200
    assert len(response.json()) == 0

    create_response_1 = authenticated_client.post(
        "/experiment",
        data=sample_experiment.model_dump_json(),
    )
    assert create_response_1.status_code == 200

    response = authenticated_client.get("/experiment")
    assert response.status_code == 200
    assert len(response.json()) == 1


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


@pytest.mark.dependency(depends=["test_create_experiment_succeeds", "test_list_experiments"])
def test_get_experiment_by_id(
    authenticated_client: TestClient,
    sample_experiment: Experiment,
):
    # arrange
    authenticated_client.post(
        "/experiment",
        data=sample_experiment.model_dump_json(),
    )
    response = authenticated_client.get("/experiment")
    experiment_id = next(iter(response.json().keys()))

    # act
    response = authenticated_client.get(f"/experiment/{experiment_id}")

    # assert
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
