from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from shepherd_core import fw_tools
from shepherd_core.data_models import FirmwareDType
from shepherd_core.data_models import GpioTracing
from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware
from shepherd_core.data_models.experiment import Experiment
from shepherd_core.data_models.experiment import TargetConfig
from shepherd_core.data_models.testbed import MCU
from shepherd_core.data_models.task import TestbedTasks
from shepherd_core.data_models.testbed import Testbed

from shepherd_wsrv.api_experiment.models import WebExperiment
from shepherd_wsrv.api_instance import app
from shepherd_wsrv.api_user.models import User
from shepherd_wsrv.api_user.utils_mail import MailEngine
from shepherd_wsrv.api_user.utils_mail import mail_engine
from shepherd_wsrv.api_user.utils_misc import calculate_password_hash
from shepherd_wsrv.db_instance import db_client


# TODO convert to autofixture?
@pytest_asyncio.fixture
async def database_for_tests(
    scheduled_experiment_id: str,
    running_experiment_id: str,
    finished_experiment_id: str,
    sample_experiment: Experiment,
):
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

    scheduled_web_experiment = WebExperiment(
        id=UUID(scheduled_experiment_id),
        experiment=sample_experiment,
        owner=working_user,
        requested_execution_at=datetime.now(),
    )
    await WebExperiment.insert_one(scheduled_web_experiment)

    running_web_experiment = WebExperiment(
        id=UUID(running_experiment_id),
        experiment=sample_experiment,
        owner=working_user,
        requested_execution_at=datetime.now(),
        started_at=datetime.now(),
    )
    await WebExperiment.insert_one(running_web_experiment)

    testbed = Testbed(name="unit_testing_testbed")
    finished_web_experiment = WebExperiment(
        id=UUID(finished_experiment_id),
        experiment=sample_experiment,
        testbed_tasks=TestbedTasks.from_xp(sample_experiment, testbed),
        owner=working_user,
        requested_execution_at=datetime.now(),
        started_at=datetime.now(),
        finished_at=datetime.now(),
    )
    await WebExperiment.insert_one(finished_web_experiment)


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
        self.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
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
        self.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
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


@pytest.fixture
def scheduled_experiment_id():
    return "00000000-0000-0000-0000-123400000001"


@pytest.fixture
def running_experiment_id():
    return "00000000-0000-0000-0000-123400000002"


@pytest.fixture
def finished_experiment_id():
    return "00000000-0000-0000-0000-123400000003"
