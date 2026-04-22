from datetime import datetime
from datetime import timedelta
from uuid import UUID

import requests
from pydantic import EmailStr
from pydantic import HttpUrl
from pydantic import validate_call
from shepherd_core.logger import log

from .client_user import UserClient
from .config import PasswordStr


class AdminClient(UserClient):
    @validate_call
    def __init__(
        self,
        account_email: EmailStr | None = None,
        password: PasswordStr | None = None,
        server: HttpUrl | None = None,
        *,
        save_credentials: bool = False,
    ) -> None:
        super().__init__(
            server=server,
            account_email=account_email,
            password=password,
            save_credentials=save_credentials,
            debug=True,
        )
        if self.get_account_info().get("role") != "admin":
            log.warning("You are not an admin - this client won't work")
        self.commands: list[str] | None = None

    # ####################################################################
    # Account Handling
    # ####################################################################

    def register_account(self, token: str) -> None:
        """Registration not possible."""
        raise NotImplementedError

    def approve_account(self, user: EmailStr) -> None:
        """Approve Account for registration.

        This will also send out an email for account verification.
        """
        data = {"email": user}
        rsp = self._req("post", "/accounts/approve", json=data)
        if not rsp.ok:
            log.warning("Approval of '%s' failed with: %s", user, self._msg(rsp))
        else:
            log.info("Approval of '%s' succeeded, token: %s", user, rsp.content.decode())

    def change_account_state(self, user: EmailStr, *, enabled: bool) -> None:
        data = {"email": user, "enabled": enabled}
        rsp = self._req("post", "/accounts/change_state", json=data)
        if not rsp.ok:
            log.warning("User-State-Change of '%s' failed with: %s", user, self._msg(rsp))
        else:
            log.info("User-State-Change of '%s' succeeded", user)

    def extend_quota(
        self,
        account_email: EmailStr,
        duration: timedelta | None = None,
        storage: int | None = None,
        expire_date: datetime | None = None,
    ) -> None:
        """Extend account limitations of a user-account.

        Only non-None fields get set by the API.
        """
        data = {
            "email": account_email,
            "quota": {
                "custom_quota_expire_date": expire_date,
                "custom_quota_duration": duration,
                "custom_quota_storage": storage,
            },
        }
        rsp = self._req("patch", "/accounts/quota", json=data)
        if not rsp.ok:
            log.warning("Extension of Quota failed with: %s", self._msg(rsp))
        else:
            log.info("Extension of Quota succeeded with: %s", rsp.json())

    # ####################################################################
    # Testbed-Handling
    # ####################################################################

    def set_restrictions(self, restrictions: list[str]) -> None:
        data = {"value": restrictions}
        rsp = self._req("patch", "/testbed/restrictions", json=data)
        if not rsp.ok:
            log.warning("Updating Restrictions failed with: %s", self._msg(rsp))
        else:
            log.info("Updating Restrictions succeeded with: %s", rsp.reason)

    def get_commands(self) -> list[str]:
        rsp = self._req("get", "/testbed/command")
        if not rsp.ok:
            log.warning("Query for commands failed with: %s", self._msg(rsp))
            return []
        return rsp.json()

    def send_command(self, cmd: str) -> None:
        if self.commands is None:
            self.commands = self.get_commands()
        if cmd not in self.commands:
            log.warning("Command is not supported -> won't try")
            return
        try:
            rsp = requests.patch(
                url=f"{self._cfg.server}testbed/command",
                json={"value": cmd},
                headers=self._auth,
                timeout=30,
            )
        except requests.Timeout:
            msg = "Command timed out."
            raise ConnectionError(msg) from None
        except requests.ConnectionError:
            msg = "Command failed."
            raise ConnectionError(msg) from None
        if not rsp.ok:
            log.warning("Starting command failed with: %s", self._msg(rsp))
        else:
            log.info("Starting command succeeded with: %s", rsp.json())

    # ####################################################################
    # Experiments
    # ####################################################################

    def list_all_experiments(self, *, only_finished: bool = False) -> list[UUID]:
        """Query experiment-IDs (from all users, even deleted ones)."""
        rsp = self._req("get", "/experiments/all")
        if not rsp.ok:
            return []
        if only_finished:
            return [key for key, value in rsp.json().items() if value == "finished"]
        return list(rsp.json().keys())
