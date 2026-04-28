from shepherd_core.config import core_config
from shepherd_core.testbed_client import tb_client

from shepherd_server.config import server_config


def prepare_fixture_client() -> None:
    core_config.testbed_name = server_config.testbed_name
    core_config.TESTBED_SERVER = server_config.server_url()
    # TODO: set PATHS_ALLOWED later
    core_config.validate_infrastructure = True
    tb_client.fixture_cache.complete_fixtures()
