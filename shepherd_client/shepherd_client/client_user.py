"""Client-Class to access a testbed instance over the web."""

import shutil
from pathlib import Path
from uuid import UUID

import certifi
import requests
from pydantic import EmailStr
from pydantic import HttpUrl
from pydantic import validate_call
from requests import JSONDecodeError
from requests import Response
from shepherd_core.data_models import Experiment
from shepherd_core.logger import increase_verbose_level
from shepherd_core.logger import log
from shepherd_core.version import version as core_version

from .client_web import WebClient
from .config import Config
from .config import PasswordStr
from .version import version as client_version


def msg(rsp: Response) -> str:
    try:
        return f"{rsp.reason} - {rsp.json()['detail']}"
    except JSONDecodeError:
        return f"{rsp.reason}"


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
        self._cfg = Config.from_file()
        if server is not None:
            self._cfg.server = server
        if user_email is not None:
            self._cfg.user_email = user_email
        if password is not None:
            self._cfg.password = password
        if save_credentials:
            self._cfg.to_file()
        super().__init__()
        self.status()
        self._auth: dict | None = None
        self.authenticate()

    # ####################################################################
    # Testbed-Status
    # ####################################################################

    def status(self) -> None:
        rsp = requests.get(
            url=f"{self._cfg.server}/",
            timeout=3,
        )
        if rsp.ok:
            state = rsp.json()
            scheduler = state.get("scheduler")
            if isinstance(scheduler, dict):
                active = scheduler.get("activated")
                if active is None:
                    log.warning("Scheduler not active!")
            if client_version != state.get("server_version"):
                log.warning("Your client version does not match with server -> consider upgrading")
                log.debug("client %s vs %s on server", client_version, state.get("server_version"))
            if core_version != state.get("core_version"):
                log.warning(
                    "Your version of shepherd-core does not match with server -> consider upgrading"
                )
                log.debug("client %s vs %s on server", core_version, state.get("core_version"))
        else:
            log.warning("Failed to fetch status from WebApi: %s", msg(rsp))

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
            verify=certifi.where(),  # optional
        )
        if rsp.ok:
            self._auth = {"Authorization": f"Bearer {rsp.json()['access_token']}"}
        else:
            log.warning("Authentication failed with: %s", msg(rsp))

    def register_account(self, token: str) -> None:
        """Create a user account with a valid token."""
        if self._auth is not None:
            log.error("User already registered and authenticated")
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
            log.info(f"User {self._cfg.user_email} registered - check mail to verify account.")
        else:
            log.warning("Registration failed with: %s", msg(rsp))

    def register_user(self, token: str) -> None:
        return self.register_account(token)  # TODO: deprecate _user()-fn

    def delete_account(self) -> None:
        """Remove account and content from server."""
        rsp = requests.delete(
            url=f"{self._cfg.server}/user",
            headers=self._auth,
            timeout=3,
        )
        if rsp.ok:
            log.info(f"User {self._cfg.user_email} deleted")
        else:
            log.warning("User-Deletion failed with: %s", msg(rsp))

    def delete_user(self) -> None:
        return self.delete_user()  # TODO: deprecate _user()-fn

    def get_user_info(self) -> dict:
        """Query user info stored on the server."""
        rsp = requests.get(
            url=f"{self._cfg.server}/user",
            headers=self._auth,
            timeout=3,
        )
        if rsp.ok:
            info = rsp.json()
            log.debug("User-Info: %s", info)
        else:
            log.warning("Query for User-Info failed with: %s", msg(rsp))
            info = {}
        return info

    def get_account_info(self) -> dict:
        return self.get_user_info()  # TODO: deprecate _user()-fn

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
            log.warning("Experiment creation failed with: %s", msg(rsp))
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
            log.warning("Getting experiment failed with: %s", msg(rsp))
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
            log.warning("Deleting experiment failed with: %s", msg(rsp))
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
            log.warning("Getting experiment state failed with: %s", msg(rsp))
            return None

        state = rsp.json()
        log.info("Experiment state: %s", state)
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
            log.info("Experiment %s scheduled", xp_id)
        else:
            log.warning("Scheduling experiment failed with: %s", msg(rsp))
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
            log.warning("File already exists - will skip download: %s", path_file)
        rsp = requests.get(
            f"{self._cfg.server}/experiment/{xp_id}/download/{node_id}",
            headers=self._auth,
            timeout=3,
            stream=True,
        )
        if not rsp.ok:
            log.warning("Downloading %s - %s failed with: %s", xp_id, node_id, msg(rsp))
            return False
        with path_file.open("wb") as fp:
            shutil.copyfileobj(rsp.raw, fp)
        log.info("Download of file completed: %s", path_file)
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
        xp.to_file(path_xp / "experiment_config.yaml", comment=f"Shepherd Nova ID: {xp_id}")
        downloads_ok: bool = True
        for node_id in node_ids:
            downloads_ok &= self._download_file(xp_id, node_id, path_xp)
        if delete_on_server:
            self.delete_experiment(xp_id)
        return downloads_ok
