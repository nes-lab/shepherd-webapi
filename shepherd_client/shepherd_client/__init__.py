from importlib.metadata import version

from .client_admin import AdminClient
from .client_user import UserClient as Client

__version__ = version("shepherd_client")

__all__ = [
    "AdminClient",
    "Client",
]
