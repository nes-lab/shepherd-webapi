"""Client-Class to access a testbed instance over the web."""

import shutil
from pathlib import Path
from uuid import UUID

import requests
from pydantic import EmailStr
from pydantic import HttpUrl
from pydantic import validate_call
from requests import Response
from shepherd_core import logger
from shepherd_core.data_models import Experiment
from shepherd_core.logger import increase_verbose_level

from .client_web import WebClient
from .config import Cfg
from .config import PasswordStr


def msg(rsp: Response) -> str:
    return f"{rsp.reason} - {rsp.json()['detail']}"


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
        user_email: EmailStr | None = None,
        password: PasswordStr | None = None,
        server: HttpUrl | None = None,
        *,
        save_credentials: bool = False,
        debug: bool = False,
    ) -> None:
        """Connect to Testbed-Server with optional account-credentials.

        user_email: your account name - used to send status updates
        password: your account safety - can be omitted and token is automatically created
        server: optional address to testbed-server-endpoint
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
            logger.warning("Authentication failed with: %s", msg(rsp))

    def register_user(self, token: str) -> None:
        """Create a user account with a valid token."""
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
            logger.warning("Registration failed with: %s", msg(rsp))

    def delete_user(self) -> None:
        """Remove account and content from server."""
        rsp = requests.delete(
            url=f"{self._cfg.server}/user",
            headers=self._auth,
            timeout=3,
        )
        if rsp.ok:
            logger.info(f"User {self._cfg.user_email} deleted")
        else:
            logger.warning("User-Deletion failed with: %s", msg(rsp))

    def get_user_info(self) -> dict:
        """Query user info stored on the server."""
        rsp = requests.get(
            url=f"{self._cfg.server}/user",
            headers=self._auth,
            timeout=3,
        )
        if rsp.ok:
            info = rsp.json()
            logger.debug("User-Info: %s", info)
        else:
            logger.warning("Query for User-Info failed with: %s", msg(rsp))
            info = {}
        return info

    # ####################################################################
    # Experiments
    # ####################################################################

    def list_experiments(self, *, only_finished: bool = False) -> dict[UUID, str]:
        """Query users experiments and their state (chronological order)."""
        rsp = requests.get(
            url=f"{self._cfg.server}/experiment",
            headers=self._auth,
            timeout=3,
        )
        if not rsp.ok:
            return {}
        if only_finished:
            return {key: value for key, value in rsp.json().items() if value == "finished"}
        return rsp.json()

    def create_experiment(self, xp: Experiment) -> UUID | None:
        """Upload a local experiment to the testbed.

        Will return the new UUID if successful.
        """
        rsp = requests.post(
            url=f"{self._cfg.server}/experiment",
            data=xp.model_dump_json(),
            headers=self._auth,
            timeout=3,
        )
        if not rsp.ok:
            logger.warning("Experiment creation failed with: %s", msg(rsp))
            return None
        return UUID(rsp.json())

    def get_experiment(self, xp_id: UUID) -> Experiment | None:
        """Request the experiment config matching the UUID."""
        rsp = requests.get(
            url=f"{self._cfg.server}/experiment/{xp_id}",
            headers=self._auth,
            timeout=3,
        )
        if not rsp.ok:
            logger.warning("Getting experiment failed with: %s", msg(rsp))
            return None

        return Experiment(**rsp.json())

    def delete_experiment(self, xp_id: UUID) -> bool:
        """Delete the experiment config matching the UUID."""
        rsp = requests.delete(
            url=f"{self._cfg.server}/experiment/{xp_id}",
            headers=self._auth,
            timeout=3,
        )
        if not rsp.ok:
            logger.warning("Deleting experiment failed with: %s", msg(rsp))
        return rsp.ok

    def get_experiment_state(self, xp_id: UUID) -> str | None:
        """Get state of a specific experiment.

        Redundant to list_experiments().
        """
        rsp = requests.get(
            url=f"{self._cfg.server}/experiment/{xp_id}/state",
            headers=self._auth,
            timeout=3,
        )
        if not rsp.ok:
            logger.warning("Getting experiment state failed with: %s", msg(rsp))
            return None

        state = rsp.json()
        logger.info("Experiment state: %s", state)
        return state

    def schedule_experiment(self, xp_id: UUID) -> bool:
        """Enter the experiment into the queue.

        Only possible if they never run before (state is "created").
        """
        rsp = requests.post(
            url=f"{self._cfg.server}/experiment/{xp_id}/schedule",
            headers=self._auth,
            timeout=3,
        )
        if rsp.ok:
            logger.info("Experiment %s scheduled", xp_id)
        else:
            logger.warning("Scheduling experiment failed with: %s", msg(rsp))
        return rsp.ok

    def _get_experiment_downloads(self, xp_id: UUID) -> list[str] | None:
        """Query all endpoints for a specific experiment."""
        rsp = requests.get(
            url=f"{self._cfg.server}/experiment/{xp_id}/download",
            headers=self._auth,
            timeout=3,
        )
        if not rsp.ok:
            return None
        return rsp.json()

    def _download_file(self, xp_id: UUID, node_id: str, path: Path) -> bool:
        """Download a specific node/observer-file for a finished experiment."""
        path_file = path / f"{node_id}.h5"
        if path_file.exists():
            logger.warning("File already exists - will skip download: %s", path_file)
        rsp = requests.get(
            f"{self._cfg.server}/experiment/{xp_id}/download/{node_id}",
            headers=self._auth,
            timeout=3,
            stream=True,
        )
        if not rsp.ok:
            logger.warning("Downloading %s - %s failed with: %s", xp_id, node_id, msg(rsp))
            return False
        with path_file.open("wb") as fp:
            shutil.copyfileobj(rsp.raw, fp)
        logger.info("Download of file completed: %s", path_file)
        return True

    def download_experiment(
        self,
        xp_id: UUID,
        path: Path,
        *,
        delete_on_server: bool = False,
    ) -> bool:
        """Download all files from a finished experiment.

        The files are stored in subdirectory of the path that was provided.
        Existing files are not overwritten, so only missing files are (re)downloaded.
        """
        xp = self.get_experiment(xp_id)
        if xp is None:
            return False
        node_ids = self._get_experiment_downloads(xp_id)
        if node_ids is None:
            return False
        path_xp = path / xp.folder_name()
        path_xp.mkdir(parents=True, exist_ok=True)
        downloads_ok: bool = True
        for node_id in node_ids:
            downloads_ok &= self._download_file(xp_id, node_id, path_xp)
        if delete_on_server:
            self.delete_experiment(xp_id)
        return downloads_ok
