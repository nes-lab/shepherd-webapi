from shepherd_core.config import config
from shepherd_core.testbed_client import tb_client

from shepherd_server.config import server_config


def prepare_fixture_client() -> None:
    config.TESTBED = server_config.testbed_name
    # TODO: set TESTBED_SERVER & PATHS_ALLOWED later
    config.VALIDATE_INFRA = True
    tb_client.fixture_cache.complete_fixtures()
