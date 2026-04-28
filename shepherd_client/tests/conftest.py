import os
from collections.abc import Generator
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from unittest import mock
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
import pytest_asyncio
from shepherd_client.client_user import UserClient
from shepherd_core import fw_tools
from shepherd_core.config import core_config
from shepherd_core.data_models.base.timezone import local_tz
from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware
from shepherd_core.data_models.content.enum_datatypes import FirmwareDType
from shepherd_core.data_models.experiment import Experiment
from shepherd_core.data_models.experiment import GpioTracing
from shepherd_core.data_models.experiment import TargetConfig
from shepherd_core.data_models.experiment import UartLogging
from shepherd_core.data_models.task import TestbedTasks
from shepherd_core.data_models.testbed import MCU
from shepherd_core.data_models.testbed import Testbed
from shepherd_core.testbed_client import AbcClient
from shepherd_core.writer import Writer as CoreWriter
from shepherd_herd import Herd
from shepherd_server.api_accounts.models import User
from shepherd_server.api_accounts.models import UserRole
from shepherd_server.api_accounts.utils_mail import MailEngine
from shepherd_server.api_accounts.utils_misc import calculate_password_hash
from shepherd_server.api_experiments.models import WebExperiment
from shepherd_server.api_testbed.models_status import TestbedDB
from shepherd_server.config import server_config as server_cfg
from shepherd_server.instance_api import run as run_api_server
from shepherd_server.instance_db import db_available
from shepherd_server.instance_db import db_client
from shepherd_server.instance_scheduler import run as run_scheduler_server

from shepherd_client import AdminClient
from shepherd_client import TestbedClient

# switch core-lib to another fixture
core_config.testbed_name = "unit_testing_testbed"
server_cfg.mail_enabled = False


@pytest_asyncio.fixture
async def _primed_database(
    scheduled_experiment_id: UUID,
    running_experiment_id: UUID,
    finished_experiment_id: UUID,
    sample_experiment: Experiment,
    tmp_path: Path,
) -> None:
    await db_client()

    await User.delete_all()
    await WebExperiment.delete_all()
    await TestbedDB.delete_all()

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

    second_user = user.model_copy(deep=True)
    second_user.email = "user2@test.com"
    await User.insert_one(second_user)

    admin_user = user.model_copy(deep=True)
    admin_user.email = "admin@test.com"
    admin_user.role = UserRole.admin
    await User.insert_one(admin_user)

    unconfirmed_user = user.model_copy(deep=True)
    unconfirmed_user.email = "unconfirmed_mail@test.com"
    unconfirmed_user.password_hash = ""
    unconfirmed_user.email_confirmed_at = None
    unconfirmed_user.token_verification = "very-secure-token"
    await User.insert_one(unconfirmed_user)

    deactivated_user = user.model_copy(deep=True)
    deactivated_user.email = "deactivated_mail@test.com"
    deactivated_user.disabled = True
    await User.insert_one(deactivated_user)

    scheduled_web_experiment = WebExperiment(
        id=scheduled_experiment_id,
        experiment=sample_experiment,
        owner=working_user,
        requested_execution_at=datetime.now(tz=local_tz()),
    )
    await WebExperiment.insert_one(scheduled_web_experiment)

    running_web_experiment = WebExperiment(
        id=running_experiment_id,
        experiment=sample_experiment,
        owner=working_user,
        requested_execution_at=datetime.now(tz=local_tz()),
        started_at=datetime.now(tz=local_tz()),
    )
    await WebExperiment.insert_one(running_web_experiment)

    # TODO: the part below could also be done by the scheduler
    finished_web_xp = WebExperiment(
        id=finished_experiment_id,
        experiment=sample_experiment,
        owner=working_user,
        requested_execution_at=datetime.now(tz=local_tz()),
        started_at=datetime.now(tz=local_tz()),
        finished_at=datetime.now(tz=local_tz()),
    )
    # mock files
    testbed = Testbed(
        name="unit_testing_testbed",
        data_on_server=tmp_path,  # path gets discarded after tests
        data_on_observer=tmp_path,
    )
    testbed_tasks = TestbedTasks.from_xp(finished_web_xp.experiment, testbed)
    finished_web_xp.result_paths = testbed_tasks.get_output_paths()
    for name, _path in finished_web_xp.result_paths.items():
        with CoreWriter(_path) as writer:
            writer.store_hostname(name)
    await WebExperiment.insert_one(finished_web_xp)


@pytest.fixture
def testbed_client(*, _server_scheduler_up: bool) -> AbcClient:
    assert _server_scheduler_up
    return TestbedClient(server=server_cfg.server_url(), debug=True)


@pytest.fixture
def user1_client(*, _server_scheduler_up: bool) -> AbcClient:
    # TODO: transform these into generators that add and clear these to DB
    assert _server_scheduler_up
    return UserClient(
        account_email="user@test.com",
        password="safe-password",
        server=server_cfg.server_url(),
        debug=True,
    )


@pytest.fixture
def user2_client(*, _server_scheduler_up: bool) -> AbcClient:
    assert _server_scheduler_up
    return UserClient(
        account_email="user2@test.com",
        password="safe-password",
        server=server_cfg.server_url(),
        debug=True,
    )


@pytest.fixture
def unknown_client(*, _server_scheduler_up: bool) -> AbcClient:
    # TODO: this loads local files, should we fake FS? done in sheep-tests
    assert _server_scheduler_up
    return UserClient(
        account_email="unknown_mail@test.com",
        password="safe-password",
        server=server_cfg.server_url(),
        debug=True,
    )


@pytest.fixture
def unconfirmed_client(*, _server_scheduler_up: bool) -> AbcClient:
    assert _server_scheduler_up
    return UserClient(
        account_email="unconfirmed_mail@test.com",
        password="safe-password",
        server=server_cfg.server_url(),
        debug=True,
    )


@pytest.fixture
def deactivated_client(*, _server_scheduler_up: bool) -> AbcClient:
    assert _server_scheduler_up
    return UserClient(
        account_email="deactivated_mail@test.com",
        password="safe-password",
        server=server_cfg.server_url(),
        debug=True,
    )


@pytest.fixture
def admin_client(*, _server_scheduler_up: bool) -> AbcClient:
    assert _server_scheduler_up
    return AdminClient(
        account_email="admin@test.com",
        password="safe-password",
        server=server_cfg.server_url(),
    )


@mock.patch("shepherd_server.api_accounts.utils_mail.FastMailEngine")
class MockMailEngine(MailEngine):
    def __init__(self) -> None:
        self.send_verification_email = AsyncMock()
        self.send_password_reset_email = AsyncMock()
        self.send_approval_email = AsyncMock()
        self.send_registration_complete_email = AsyncMock()


@pytest.fixture(scope="module")
def mock_mail_engine() -> MockMailEngine:
    from shepherd_server.api_accounts.utils_mail import set_mail_engine

    mocki = MockMailEngine()
    set_mail_engine(mocki)
    return mocki


@pytest.fixture
def mail_engine() -> MailEngine:
    from shepherd_server.api_accounts.utils_mail import get_mail_engine

    return get_mail_engine()


@pytest.fixture(scope="module")
def cfg_env() -> bool:
    os.environ["MAIL_ENABLED"] = "False"
    os.environ["AUTH_SALT"] = "salty_business"
    os.environ["ROOT_URL"] = "127.0.0.1"
    return True


@pytest.fixture(scope="module")  # restarts once per module
def _server_api_up(
    *, cfg_env: bool, mock_mail_engine: MockMailEngine
) -> Generator[bool, None, None]:
    assert cfg_env
    assert mock_mail_engine
    assert db_available(timeout=2)
    with pytest.raises(ConnectionError):
        # Test if another API is running that will interfere
        TestbedClient(server=server_cfg.server_url(), timeout=1, debug=True).testbed_name()
    # TODO: could just use Process(target=run_api_server) & .start()
    with ProcessPoolExecutor() as pool:
        pool.submit(run_api_server)
        yield True
        for proc in pool._processes.values():  # noqa: SLF001
            # hacky: ppe.shutdown() does not work on infinite tasks
            proc.terminate()


@pytest.fixture
def _server_scheduler_up(*, cfg_env: bool) -> Generator[bool, None, None]:
    assert cfg_env
    with ProcessPoolExecutor() as pool:
        pool.submit(run_scheduler_server, dry_run=True)
        yield True
        for proc in pool._processes.values():  # noqa: SLF001
            # hacky: ppe.shutdown() does not work on infinite tasks
            proc.terminate()


def herd_present() -> bool:
    try:
        _ = Herd()
    except FileNotFoundError:
        return False
    return True


@pytest.fixture
def sample_target_config() -> TargetConfig:
    firmware_path = (
        Path(__file__).parent.parent.parent / "shepherd_server/tests/data/test-firmware-nrf52.elf"
    )
    return TargetConfig(
        target_IDs=[42],
        energy_env=EnergyEnvironment(name="synthetic_static_3000mV_50mA"),
        firmware1=Firmware(
            name="FW_TestXYZ",
            data=fw_tools.file_to_base64(firmware_path),
            data_type=FirmwareDType.base64_elf,
            data_2_copy=False,
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
def scheduled_experiment_id() -> UUID:
    # TODO: transform these into generators that add and clear these to DB
    return UUID("00000000-0000-0000-0000-123400000001")


@pytest.fixture
def running_experiment_id() -> UUID:
    return UUID("00000000-0000-0000-0000-123400000002")


@pytest.fixture
def finished_experiment_id() -> UUID:
    return UUID("00000000-0000-0000-0000-123400000003")
