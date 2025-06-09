from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from shepherd_core import Writer as CoreWriter
from shepherd_core import fw_tools
from shepherd_core import local_tz
from shepherd_core.data_models import FirmwareDType
from shepherd_core.data_models import GpioTracing
from shepherd_core.data_models import UartLogging
from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware
from shepherd_core.data_models.experiment import Experiment
from shepherd_core.data_models.experiment import TargetConfig
from shepherd_core.data_models.task import TestbedTasks
from shepherd_core.data_models.testbed import MCU
from shepherd_core.data_models.testbed import Testbed
from shepherd_server.api_experiment.models import WebExperiment
from shepherd_server.api_user.models import User
from shepherd_server.api_user.utils_mail import MailEngine
from shepherd_server.api_user.utils_mail import mail_engine
from shepherd_server.api_user.utils_misc import calculate_password_hash
from shepherd_server.instance_api import app
from shepherd_server.instance_db import db_client


@pytest_asyncio.fixture
async def database_for_tests(
    scheduled_experiment_id: str,
    running_experiment_id: str,
    finished_experiment_id: str,
    sample_experiment: Experiment,
    tmp_path: Path,
) -> bool:
    await db_client()

    await User.delete_all()
    await WebExperiment.delete_all()

    user = User(
        email="user@test.com",
        password_hash=calculate_password_hash("safe-password"),
        first_name="first name",
        last_name="last name",
        disabled=False,
        email_confirmed_at=datetime.now(tz=local_tz()),
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
        requested_execution_at=datetime.now(tz=local_tz()),
    )
    await WebExperiment.insert_one(scheduled_web_experiment)

    running_web_experiment = WebExperiment(
        id=UUID(running_experiment_id),
        experiment=sample_experiment,
        owner=working_user,
        requested_execution_at=datetime.now(tz=local_tz()),
        started_at=datetime.now(tz=local_tz()),
    )
    await WebExperiment.insert_one(running_web_experiment)

    # TODO: the part below could also be done by the scheduler
    testbed = Testbed(
        name="unit_testing_testbed",
        data_on_server=tmp_path,  # path gets discarded after tests
        data_on_observer=tmp_path,
    )
    finished_web_experiment = WebExperiment(
        id=UUID(finished_experiment_id),
        experiment=sample_experiment,
        testbed_tasks=TestbedTasks.from_xp(sample_experiment, testbed),
        owner=working_user,
        requested_execution_at=datetime.now(tz=local_tz()),
        started_at=datetime.now(tz=local_tz()),
        finished_at=datetime.now(tz=local_tz()),
    )
    # mock files
    finished_web_experiment.result_paths = finished_web_experiment.testbed_tasks.get_output_paths()
    for name, _path in finished_web_experiment.result_paths.items():
        with CoreWriter(_path) as writer:
            writer.store_hostname(name)
    await WebExperiment.insert_one(finished_web_experiment)
    return True


class UserTestClient(TestClient):
    """Raw-User-Client

    A few notes for avoiding pits:

    - requests like .patch(), ... have a data AND json argument
    - data is for completely serialized objects like model.model_dump_json()
    - json digests dicts, self-assembled, composed with .model_dump(mode="json")
        - mixing json-strings and dicts won't work, i.e. {"quota": quota.model_dump_json()}
        - .model_dump() may produce dicts that are not json-serializable
    """

    @contextmanager
    def authenticate_admin(self) -> Generator[TestClient, None, None]:
        response = self.post(
            "/auth/token",
            data={
                "username": "admin@test.com",
                "password": "safe-password",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        self.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
        yield self
        self.headers["Authorization"] = ""

    @contextmanager
    def authenticate_user(self) -> Generator[TestClient, None, None]:
        response = self.post(
            "/auth/token",
            data={
                "username": "user@test.com",
                "password": "safe-password",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        self.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
        yield self
        self.headers["Authorization"] = ""

    @contextmanager
    def regular_joe(self) -> Generator[TestClient, None, None]:
        self.headers["Authorization"] = ""
        yield self


@pytest.fixture
def client(*, database_for_tests: bool) -> Generator[TestClient, None, None]:
    assert database_for_tests
    with UserTestClient(app) as client:
        yield client


# @mock.patch("shepherd_server.api_user.utils_mail.FastMailEngine")
class MockMailEngine(MailEngine):
    def __init__(self) -> None:
        self.send_verification_email = AsyncMock()
        self.send_password_reset_email = AsyncMock()
        self.send_approval_email = AsyncMock()
        self.send_registration_complete_email = AsyncMock()


@pytest.fixture
def mail_engine_mock() -> MailEngine:
    mock_engine = MockMailEngine()
    app.dependency_overrides[mail_engine] = lambda: mock_engine
    return mock_engine


@pytest.fixture
def sample_target_config() -> TargetConfig:
    firmware_path = Path(__file__).parent / "data/test-firmware-nrf52.elf"
    return TargetConfig(
        target_IDs=[42],
        energy_env=EnergyEnvironment(name="eenv_static_3000mV_50mA_3600s"),
        firmware1=Firmware(
            name="FW_TestXYZ",
            data=fw_tools.file_to_base64(firmware_path),
            data_type=FirmwareDType.base64_elf,
            data_local=True,
            mcu=MCU(name="nRF52"),
        ),
        power_tracing=None,
        uart_logging=UartLogging(baudrate=115_200),
        gpio_tracing=GpioTracing(),
    )


@pytest.fixture
def sample_experiment(sample_target_config: TargetConfig) -> Experiment:
    return Experiment(
        name="test-experiment",
        duration=30,
        target_configs=[sample_target_config],
    )


@pytest.fixture
def scheduled_experiment_id() -> str:
    return "00000000-0000-0000-0000-123400000001"


@pytest.fixture
def running_experiment_id() -> str:
    return "00000000-0000-0000-0000-123400000002"


@pytest.fixture
def finished_experiment_id() -> str:
    return "00000000-0000-0000-0000-123400000003"
