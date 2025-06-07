"""Client-Class to access a testbed instance over the web."""

import requests
from pydantic import EmailStr
from pydantic import HttpUrl
from pydantic import validate_call
from shepherd_core import logger
from shepherd_core.logger import increase_verbose_level

from .client_web import WebClient
from .config import Cfg
from .config import PasswordStr


class UserClient(WebClient):
    """Client-Class to access a testbed instance over the web.

    For online-queries the lib can be connected to the testbed-server.
    NOTE: there are 4 states:
    - unconnected -> demo-fixtures are queried (locally), TODO: remove
    - connected -> publicly available data is queried online
    - unregistered -> calling init triggers account-registration
    - validated account -> also private data is queried online, option to schedule experiments
    """

    @validate_call
    def __init__(
        self,
        server: HttpUrl | None = None,
        user_email: EmailStr | None = None,
        password: PasswordStr | None = None,
        *,
        save_credentials: bool = False,
        debug: bool = False,
    ) -> None:
        """Connect to Testbed-Server with optional account-credentials.

        server: optional address to testbed-server-endpoint
        user_email: your account name - used to send status updates
        password: your account safety - can be omitted and token is automatically created
        save_credentials: your inputs will be saved to your account (XDG-path or user/.config/), so you can avoid entering them here
        """
        if debug:
            increase_verbose_level(3)

        self._cfg = Cfg.from_file()
        if server is not None:
            self._cfg.server = server
        if user_email is not None:
            self._cfg.user_email = user_email
        if password is not None:
            self._cfg.password = password
        if save_credentials:
            self._cfg.to_file()
        super().__init__()

        self._connected: bool = False
        self._token: str | None = None

        self.authenticate()

    def authenticate(self) -> None:
        rsp = requests.post(
            url=f"{self._cfg.server}/auth/token",
            data={
                "username": self._cfg.user_email,
                "password": self._cfg.password,
            },
            timeout=3,
        )
        if not rsp.ok:
            logger.warning("Authentication failed with: %s", rsp.reason)
            return
        self._token = rsp.json()["access_token"]

    def register_user(self) -> None:
        if self._token is not None:
            logger.error("User already registered and authenticated")
        rsp = requests.post(
            url=f"{self._cfg.server}/user/register",
            data={
                "email": self._cfg.user_email,
                "password": self._cfg.password,
            },
            timeout=3,
        )
        if not rsp.ok:
            logger.warning("Registration failed with: %s", rsp.reason)
            return
        logger.info(f"User {self._cfg.user_email} registered - check mail to verify account.")

    def delete_user(self):
        """"""

    def get_user_info(self):
        pass

    def get_user_quota(self):
        pass
