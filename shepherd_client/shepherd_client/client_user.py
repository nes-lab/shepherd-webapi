"""Client-Class to access the server of a testbed instance over the internet."""

import shutil
from pathlib import Path
from uuid import UUID

import certifi
import requests
from pydantic import EmailStr
from pydantic import HttpUrl
from pydantic import validate_call
from shepherd_core.data_models import Experiment
from shepherd_core.logger import log
from typing_extensions import deprecated

from .client_testbed import TestbedClient
from .config import PasswordStr


class UserClient(TestbedClient):
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
        account_email: EmailStr | None = None,
        password: PasswordStr | None = None,
        server: HttpUrl | None = None,
        *,
        save_credentials: bool = False,
        debug: bool = False,
    ) -> None:
        """Connect to Testbed-Server with optional account-credentials.

        account_email: your account name - used to send status updates
        password: your account safety - can be omitted and token is automatically created
        server: optional address to testbed-server-endpoint
        save_credentials: your inputs will be saved to your account (XDG-path or user/.config/),
                          -> you won't need to enter them again
        """

        # TODO: no password and wanting to save should be disallowed, as the password would be lost

        super().__init__(server=server, debug=debug)
        if account_email is not None:
            self._cfg.account_email = account_email
        if password is not None:
            self._cfg.password = password
        if save_credentials:
            self._cfg.to_file()

        self.authenticate()

    # ####################################################################
    # Account
    # ####################################################################

    def authenticate(self) -> None:
        try:
            rsp = requests.post(
                url=f"{self._cfg.server}auth/token",
                data={
                    "username": self._cfg.account_email,
                    "password": self._cfg.password,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},  # TODO: needed?
                timeout=3,
                verify=certifi.where(),  # optional
            )
        except requests.Timeout:
            msg = "Authentication timed out."
            raise ConnectionError(msg) from None
        except requests.ConnectionError:
            msg = "Authentication failed."
            raise ConnectionError(msg) from None
        if rsp.ok:
            self._auth = {"Authorization": f"Bearer {rsp.json()['access_token']}"}
        else:
            log.warning("Authentication failed with: %s", self._msg(rsp))

    def register_account(self, token: str) -> None:
        """Create a user account with a valid token."""
        if self._auth is not None:
            log.error("User already registered and authenticated")
        data = {
            "email": self._cfg.account_email,
            "password": self._cfg.password,
            "token": token,
        }
        rsp = self._req("post", "/accounts/register", json=data)
        if rsp.ok:
            log.info(f"User {self._cfg.account_email} registered - check mail to verify account.")
        else:
            log.warning("Registration failed with: %s", self._msg(rsp))

    @deprecated("use .register_account()")
    def register_user(self, token: str) -> None:
        return self.register_account(token)

    def delete_account(self) -> None:
        """Remove account and content from server."""
        rsp = self._req("delete", "/accounts")
        if rsp.ok:
            log.info(f"User {self._cfg.account_email} deleted")
        else:
            log.warning("User-Deletion failed with: %s", self._msg(rsp))

    @deprecated("use .delete_account()")
    def delete_user(self) -> None:
        self.delete_account()

    def get_account_info(self) -> dict:
        """Query user info stored on the server."""
        rsp = self._req("get", "/accounts")
        if rsp.ok:
            info = rsp.json()
            log.debug("User-Info: %s", info)
        else:
            log.warning("Query for User-Info failed with: %s", self._msg(rsp))
            info = {}
        return info

    @deprecated("use .get_account_info()")
    def get_user_info(self) -> dict:
        return self.get_account_info()

    def request_password_reset(self) -> bool:
        data = {"email": self._cfg.account_email}
        rsp = self._req("post", "/accounts/forgot-password", json=data)
        if rsp.ok:
            log.info("Request successful - you will shortly receive an email with a reset-token.")
        else:
            log.error("Reset request was NOT successful.")
        return rsp.ok

    @validate_call
    def reset_password(self, token: str, password: str) -> bool:
        data = {
            "token": token,
            "password": password,
        }
        rsp = self._req("post", "/accounts/reset-password", json=data)
        if rsp.ok:
            log.info("Password was reset successfully.")
        else:
            log.error("Password reset was NOT successful.")
        return rsp.ok

    # ####################################################################
    # Experiments
    # ####################################################################

    def list_experiments(self, *, only_finished: bool = False) -> list[UUID]:
        """Query users experiment-IDs."""
        rsp = self._req("get", "/experiments")
        if not rsp.ok:
            return []
        if only_finished:
            return [key for key, value in rsp.json().items() if value in ["finished", "failed"]]
        return list(rsp.json().keys())

    def create_experiment(self, xp: Experiment) -> UUID | None:
        """Upload a local experiment to the testbed-server and validate its feasibility.

        Will return the new UUID if successful.
        """
        data = xp.model_dump(mode="json")
        rsp = self._req("post", "/experiments", json=data)
        if not rsp.ok:
            log.warning("Experiment creation failed with: %s", self._msg(rsp))
            return None
        return UUID(rsp.json())

    def get_experiment(self, xp_id: UUID) -> Experiment | None:
        """Request the experiment config matching the UUID."""
        rsp = self._req("get", f"/experiments/{xp_id}")
        if not rsp.ok:
            log.warning("Getting experiment failed with: %s", self._msg(rsp))
            return None

        return Experiment(**rsp.json())

    def delete_experiment(self, xp_id: UUID) -> bool:
        """Delete the experiment config matching the UUID."""
        rsp = self._req("delete", f"/experiments/{xp_id}")
        if not rsp.ok:
            log.warning("Deleting experiment failed with: %s", self._msg(rsp))
        return rsp.ok

    def get_experiment_state(self, xp_id: UUID) -> str | None:
        """Get state of a specific experiment.

        - after valid submission: created
        - after scheduling: scheduled
        - during experiment: running
        - after the run: finished or failed

        """
        rsp = self._req("get", f"/experiments/{xp_id}/state")
        if not rsp.ok:
            log.warning("Getting experiment state failed with: %s", self._msg(rsp))
            return None

        state = rsp.json()
        log.info("Experiment state: %s", state)
        return state

    def get_experiment_statistics(self, xp_id: UUID) -> dict | None:
        """Get metadata of a specific experiment (relevant for statistics).

        This contains currently: ID, state, execution-time, duration, size, owner
        """
        rsp = self._req("get", f"/experiments/{xp_id}/statistics")
        if not rsp.ok:
            log.warning("Getting experiment statistics failed with: %s", self._msg(rsp))
            return None
        return rsp.json()

    def schedule_experiment(self, xp_id: UUID) -> bool:
        """Enter the experiment into the scheduling-queue.

        Only possible if they never run before (state is "created").
        """
        rsp = self._req("post", f"/experiments/{xp_id}/schedule")
        if rsp.ok:
            log.info("Experiment %s scheduled", xp_id)
        else:
            log.warning("Scheduling experiment failed with: %s", self._msg(rsp))
        return rsp.ok

    def _get_experiment_downloads(self, xp_id: UUID) -> list[str] | None:
        """Query all endpoints for a specific experiment."""
        rsp = self._req("get", f"/experiments/{xp_id}/download")
        if not rsp.ok:
            return None
        return rsp.json()

    def _download_file(self, xp_id: UUID, node_id: str, path: Path) -> bool:
        """Download a specific node/observer-file for a finished experiment."""
        path_file = path / f"{node_id}.h5"
        if path_file.exists():
            log.warning("File already exists - will skip download: %s", path_file)
        rsp = self._req("get", f"/experiments/{xp_id}/download/{node_id}", stream=True)
        if not rsp.ok:
            log.warning("Downloading %s - %s failed with: %s", xp_id, node_id, self._msg(rsp))
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
