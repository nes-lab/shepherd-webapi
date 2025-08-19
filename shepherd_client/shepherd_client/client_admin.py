from datetime import datetime
from datetime import timedelta

import requests
from pydantic import EmailStr
from pydantic import HttpUrl
from pydantic import validate_call
from shepherd_core.logger import log

from .client_user import UserClient
from .client_user import msg
from .config import PasswordStr


class AdminClient(UserClient):
    @validate_call
    def __init__(
        self,
        admin_email: EmailStr | None = None,
        password: PasswordStr | None = None,
        server: HttpUrl | None = None,
        *,
        save_credentials: bool = False,
    ) -> None:
        super().__init__(
            server=server,
            user_email=admin_email,
            password=password,
            save_credentials=save_credentials,
            debug=True,
        )
        if self.get_user_info().get("role") != "admin":
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
        rsp = requests.post(
            url=f"{self._cfg.server}/user/approve",
            json={"email": user},
            headers=self._auth,
            timeout=3,
        )
        if not rsp.ok:
            log.warning("Approval of '%s' failed with: %s", user, msg(rsp))
        else:
            log.info("Approval of '%s' succeeded, token: %s", user, rsp.content.decode())

    def change_account_state(self, user: EmailStr, *, enabled: bool) -> None:
        rsp = requests.post(
            url=f"{self._cfg.server}/user/change_state",
            json={"email": user, "enabled": enabled},
            headers=self._auth,
            timeout=3,
        )
        if not rsp.ok:
            log.warning("User-State-Change of '%s' failed with: %s", user, msg(rsp))
        else:
            log.info("User-State-Change of '%s' succeeded", user)

    def extend_quota(
        self,
        user_email: EmailStr,
        duration: timedelta | None = None,
        storage: int | None = None,
        expire_date: datetime | None = None,
    ) -> None:
        """Extend account limitations of a user-account.

        Only non-None fields get set by the API.
        """
        quota = {
            "custom_quota_expire_date": expire_date,
            "custom_quota_duration": duration,
            "custom_quota_storage": storage,
        }
        rsp = requests.patch(
            url=f"{self._cfg.server}/user/quota",
            json={
                "email": user_email,
                "quota": quota,
            },
            headers=self._auth,
            timeout=3,
        )
        if not rsp.ok:
            log.warning("Extension of Quota failed with: %s", msg(rsp))
        else:
            log.info("Extension of Quota succeeded with: %s", rsp.json())

    # ####################################################################
    # Testbed-Handling
    # ####################################################################

    def get_restrictions(self) -> list[str]:
        rsp = requests.get(
            url=f"{self._cfg.server}/testbed/restrictions",
            timeout=3,
        )
        if not rsp.ok:
            log.warning("Query for restrictions failed with: %s", msg(rsp))
            return []
        return rsp.json()

    def set_restrictions(self, restrictions: list[str]) -> None:
        rsp = requests.patch(
            url=f"{self._cfg.server}/testbed/restrictions",
            json={"value": restrictions},
            headers=self._auth,
            timeout=3,
        )
        if not rsp.ok:
            log.warning("Updating Restrictions failed with: %s", msg(rsp))
        else:
            log.info("Updating Restrictions succeeded with: %s", rsp.reason)

    def get_commands(self) -> list[str]:
        rsp = requests.get(
            url=f"{self._cfg.server}/testbed/command",
            headers=self._auth,
            timeout=3,
        )
        if not rsp.ok:
            log.warning("Query for commands failed with: %s", msg(rsp))
            return []
        return rsp.json()

    def send_command(self, cmd: str) -> None:
        if self.commands is None:
            self.commands = self.get_commands()
        if cmd not in self.commands:
            log.warning("Command is not supported -> won't try")
            return
        rsp = requests.patch(
            url=f"{self._cfg.server}/testbed/command",
            json={"value": cmd},
            headers=self._auth,
            timeout=20,
        )
        if not rsp.ok:
            log.warning("Starting command failed with: %s", msg(rsp))
        else:
            log.info("Starting command succeeded with: %s", rsp.json())
