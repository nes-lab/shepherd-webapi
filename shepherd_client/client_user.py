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
        save_credentials: your inputs will be saved to your account (XDG-path or user/.config/),
                          -> you won't need to enter them again
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

        self._auth: dict | None = None
        self.authenticate()

    def authenticate(self) -> None:
        rsp = requests.post(
            url=f"{self._cfg.server}/auth/token",
            data={
                "username": self._cfg.user_email,
                "password": self._cfg.password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},  # TODO: needed?
            timeout=3,
        )
        if rsp.ok:
            self._auth = {"Authorization": f"Bearer {rsp.json()['access_token']}"}
        else:
            logger.warning("Authentication failed with: %s", rsp.reason)

    def register_user(self) -> None:
        if self._auth is not None:
            logger.error("User already registered and authenticated")
        rsp = requests.post(
            url=f"{self._cfg.server}/user/register",
            json={
                "email": self._cfg.user_email,
                "password": self._cfg.password,
            },
            headers=self._auth,
            timeout=3,
        )
        if rsp.ok:
            logger.info(f"User {self._cfg.user_email} registered - check mail to verify account.")
        else:
            logger.warning("Registration failed with: %s", rsp.reason)

    def delete_user(self) -> None:
        """"""
        rsp = requests.delete(
            url=f"{self._cfg.server}/user",
            headers=self._auth,
            timeout=3,
        )
        if rsp.ok:
            logger.info(f"User {self._cfg.user_email} deleted")
        else:
            logger.warning("User-Deletion failed with: %s", rsp.reason)

    def get_user_info(self) -> dict:
        rsp = requests.get(
            url=f"{self._cfg.server}/user",
            headers=self._auth,
            timeout=3,
        )
        if rsp.ok:
            info = rsp.json()
            logger.debug("User-Info: %s", info)
        else:
            logger.warning("Query for User-Info failed with: %s", rsp.reason)
            info = {}
        return info
