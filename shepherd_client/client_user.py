"""Client-Class to access a testbed instance over the web."""

import shutil
from pathlib import Path
from uuid import UUID

import requests
from pydantic import EmailStr
from pydantic import HttpUrl
from pydantic import validate_call
from shepherd_core import local_now
from shepherd_core import logger
from shepherd_core.data_models import Experiment
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
        # TODO: no password and wanting to save should be disallowed, as the password would be lost
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

    # ####################################################################
    # Account
    # ####################################################################

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

    def register_user(self, token: str) -> None:
        if self._auth is not None:
            logger.error("User already registered and authenticated")
        rsp = requests.post(
            url=f"{self._cfg.server}/user/register",
            json={
                "email": self._cfg.user_email,
                "password": self._cfg.password,
                "token": token,
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

    # ####################################################################
    # Experiments
    # ####################################################################

    def get_experiments(self) -> dict:
        rsp = requests.get(
            url=f"{self._cfg.server}/experiment",
            headers=self._auth,
            timeout=3,
        )
        # TODO: cast to experiments? YES
        return rsp.json() if rsp.ok else {}

    def create_experiment(self, xp: Experiment) -> UUID | None:
        rsp = requests.post(
            url=f"{self._cfg.server}/experiment",
            data=xp.model_dump_json(),
            headers=self._auth,
            timeout=3,
        )
        if not rsp.ok:
            logger.warning("Experiment creation failed with: %s", rsp.reason)
            return None
        return UUID(rsp.content)

    def get_experiment(self, xp_id: UUID) -> Experiment | None:
        rsp = requests.get(
            url=f"{self._cfg.server}/experiment/{xp_id}",
            headers=self._auth,
            timeout=3,
        )
        if not rsp.ok:
            logger.warning("Getting experiment failed with: %s", rsp.reason)
            return None

        return Experiment(**rsp.json())

    def delete_experiment(self, xp_id: UUID) -> bool:
        rsp = requests.delete(
            url=f"{self._cfg.server}/experiment/{xp_id}",
            headers=self._auth,
            timeout=3,
        )
        if not rsp.ok:
            logger.warning("Deleting experiment failed with: %s", rsp.reason)
        return rsp.ok

    def get_experiment_state(self, xp_id: UUID) -> str | None:
        rsp = requests.get(
            url=f"{self._cfg.server}/experiment/{xp_id}/state",
            headers=self._auth,
            timeout=3,
        )
        if not rsp.ok:
            logger.warning("Getting experiment state failed with: %s", rsp.reason)
            return None

        state = rsp.content.decode()
        logger.info("Experiment state: %s", state)
        return state

    def schedule_experiment(self, xp_id: UUID) -> bool:
        rsp = requests.post(
            url=f"{self._cfg.server}/experiment/{xp_id}/schedule",
            headers=self._auth,
            timeout=3,
        )
        if rsp.ok:
            logger.info("Experiment %s scheduled", xp_id)
        else:
            logger.warning("Scheduling experiment failed with: %s", rsp.reason)
        return rsp.ok

    def _get_experiment_downloads(self, xp_id: UUID) -> list[str] | None:
        rsp = requests.get(
            url=f"{self._cfg.server}/experiment/{xp_id}/download",
            headers=self._auth,
            timeout=3,
        )
        if not rsp.ok:
            return None
        return rsp.json()

    def _download_file(self, xp_id: UUID, node_id: str, path: Path) -> bool:
        rsp = requests.get(
            f"{self._cfg.server}/experiment/{xp_id}/download/{node_id}",
            headers=self._auth,
            timeout=3,
            stream=True,
        )
        if not rsp.ok:
            logger.warning("Downloading %s - %s failed with: %s", xp_id, node_id, rsp.reason)
            return False

        with (path / f"{node_id}.h5").open("wb") as fp:
            shutil.copyfileobj(rsp.raw, fp)
        return True

    def download_experiment(
        self,
        xp_id: UUID,
        path: Path,
        *,
        delete_on_server: bool = False,
    ) -> bool:
        xp = self.get_experiment(xp_id)
        if xp is None:
            return False
        node_ids = self._get_experiment_downloads(xp_id)
        if node_ids is None:
            return False
        timestamp = local_now() if xp.time_start is None else xp.time_start
        timestrng = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        # ⤷ closest to ISO 8601, avoids ":"
        path_xp = path / f"{timestrng}_{xp.name.replace(' ', '_')}"
        path_xp.mkdir(parents=True, exist_ok=False)
        downloads_ok: bool = True
        for node_id in node_ids:
            downloads_ok &= self._download_file(xp_id, node_id, path_xp)
        if delete_on_server:
            self.delete_experiment(xp_id)
        return downloads_ok
