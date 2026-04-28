from importlib.metadata import version

from shepherd_core.testbed_client.client_testbed import TestbedClient

from .client_admin import AdminClient
from .client_user import UserClient as Client

__version__ = version("shepherd_client")

__all__ = [
    "AdminClient",
    "Client",
    "TestbedClient",
]
