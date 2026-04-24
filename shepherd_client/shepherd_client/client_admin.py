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

    def register_account(self, token: str) -> bool:
        """Registration for your own account is not possible.

        This can only be created directly on server.
        """
        raise NotImplementedError

    def approve_account(self, account_email: EmailStr) -> str | None:
        """Approve Account for registration.

        This will also send out an email for account verification.
        """
        data = {"email": account_email}
        rsp = self._req("post", "/accounts/approve", json=data)
        if rsp.ok:
            token = rsp.content.decode()
            log.info("Approval of '%s' succeeded, token: %s", account_email, token)
            return token

        log.warning("Approval of '%s' failed with: %s", account_email, self._msg(rsp))
        return None

    def change_account_state(self, account_email: EmailStr, *, enabled: bool) -> bool:
        data = {"email": account_email, "enabled": enabled}
        rsp = self._req("post", "/accounts/change_state", json=data)
        if rsp.ok:
            log.info("Account-State-Change of '%s' succeeded", account_email)
        else:
            log.warning(
                "Account-State-Change of '%s' failed with: %s", account_email, self._msg(rsp)
            )
        return rsp.ok

    def extend_quota(
        self,
        account_email: EmailStr,
        duration: timedelta | None = None,
        storage: int | None = None,
        expire_date: datetime | None = None,
        *,
        force: bool = False,
    ) -> bool:
        """Extend account limitations of a user-account.

        Without force, only non-None fields get set by the API.
        """
        if isinstance(duration, timedelta):
            duration: float = duration.total_seconds()
        if isinstance(expire_date, datetime):
            expire_date: str = expire_date.isoformat()
        data = {
            "email": account_email,
            "quota": {
                "custom_quota_expire_date": expire_date,
                "custom_quota_duration": duration,
                "custom_quota_storage": storage,
            },
            "force": force,
        }
        rsp = self._req("patch", "/accounts/quota", json=data)
        if rsp.ok:
            log.info("Extension of Quota succeeded with: %s", rsp.json())
        else:
            log.warning("Extension of Quota failed with: %s", self._msg(rsp))
        return rsp.ok

    # ####################################################################
    # Testbed-Handling
    # ####################################################################

    def set_restrictions(self, restrictions: list[str]) -> bool:
        data = {"value": restrictions}
        rsp = self._req("patch", "/testbed/restrictions", json=data)
        if not rsp.ok:
            log.info("Updating Restrictions succeeded with: %s", rsp.reason)
        else:
            log.warning("Updating Restrictions failed with: %s", self._msg(rsp))
        return rsp.ok

    def get_commands(self) -> list[str]:
        rsp = self._req("get", "/testbed/command")
        if not rsp.ok:
            log.warning("Query for commands failed with: %s", self._msg(rsp))
            return []
        return rsp.json()

    def send_command(self, cmd: str) -> bool:
        if self.commands is None:
            self.commands = self.get_commands()
        if cmd not in self.commands:
            log.warning("Command is not supported -> won't try")
            return False
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
        if rsp.ok:
            log.info("Starting command succeeded with: %s", rsp.json())
        else:
            log.warning("Starting command failed with: %s", self._msg(rsp))
        return rsp.ok

    # ####################################################################
    # Admin Lists for Experiments & Accounts
    # ####################################################################

    def list_all_experiments(self, *, only_finished: bool = False) -> list[UUID]:
        """Query experiment-IDs (from all users, even deleted ones)."""
        rsp = self._req("get", "/experiments/all")
        if not rsp.ok:
            return []
        if only_finished:
            return [key for key, value in rsp.json().items() if value == "finished"]
        return list(rsp.json().keys())

    def list_all_accounts(self) -> list[dict]:
        """Query non-critical account data from user-DB."""
        rsp = self._req("get", "/accounts/all")
        if not rsp.ok:
            return []
        return list(rsp.json())
