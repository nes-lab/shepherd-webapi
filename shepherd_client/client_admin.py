from datetime import datetime
from datetime import timedelta

import requests
from pydantic import EmailStr
from pydantic import HttpUrl
from pydantic import validate_call
from shepherd_core import logger

from .client_user import UserClient
from .config import PasswordStr


class AdminClient(UserClient):
    @validate_call
    def __init__(
        self,
        server: HttpUrl | None = None,
        admin_email: EmailStr | None = None,
        password: PasswordStr | None = None,
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
            raise TypeError("You are not an admin")

    def register_user(self) -> None:
        """Registration not possible."""
        raise NotImplementedError

    def approve_user(self, user: EmailStr) -> None:
        """Enable Account after a user registers & validates their email."""
        rsp = requests.post(
            url=f"{self._cfg.server}/user/approve",
            json={"email": user},
            headers=self._auth,
            timeout=3,
        )
        if not rsp.ok:
            logger.warning("Approval of '%s' failed with: %s", user, rsp.reason)
        else:
            logger.info("Approval of '%s' succeeded", user)

    def extend_quota(
        self,
        user_email: EmailStr,
        duration: timedelta | None = None,
        storage: int | None = None,
        expire_date: datetime | None = None,
    ) -> None:
        """Extend account limitations of a user."""
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
            logger.warning("Extension of Quota failed with: %s", rsp.reason)
        else:
            logger.info("Extension of Quota succeeded with: %s", rsp.json())
