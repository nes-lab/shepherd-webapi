"""A basic web-client to access testbed-related content without a login."""

from collections.abc import Collection
from importlib import metadata

import requests
from pydantic import HttpUrl
from pydantic import validate_call
from requests import JSONDecodeError
from requests import Response
from shepherd_core.config import core_config
from shepherd_core.logger import increase_verbose_level
from shepherd_core.logger import log
from typing_extensions import Unpack
from typing_extensions import deprecated

from .config import ClientConfig


@deprecated
def msg(rsp: Response) -> str:
    """"""
    try:
        return f"{rsp.reason} - {rsp.json()['detail']}"
    except JSONDecodeError:
        return f"{rsp.reason}"


class ContentClient:
    @validate_call
    def __init__(self, server: HttpUrl | None = None, *, debug: bool = False) -> None:

        if debug:
            increase_verbose_level(3)
        self._cfg = ClientConfig.from_file()
        if server is not None:
            self._cfg.server = server
        self._auth: dict | None = None
        core_config.VALIDATE_INFRA = True
        # TODO: add server name and more from server
        self.status()

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
                dry_run = scheduler.get("dry_run")
                if dry_run:
                    log.warning("Scheduler is running in demo-mode (dry-run)!")
                targets_offline = scheduler.get("targets_offline")
                if isinstance(targets_offline, Collection) and len(targets_offline) > 0:
                    log.warning("One or more targets seem to be offline: %s", targets_offline)
                # TODO: could tests for last update being old
            if metadata.version("shepherd-client") != state.get("server_version"):
                log.warning("Your client version does not match with server -> consider upgrading")
                log.info(
                    "client v%s vs server v%s",
                    metadata.version("shepherd-client"),
                    state.get("server_version"),
                )
            if metadata.version("shepherd-core") != state.get("core_version"):
                log.warning(
                    "Your version of shepherd-core does not match with server -> consider upgrading"
                )
                log.info(
                    "shepherd-core on client %s vs %s on server",
                    metadata.version("shepherd-core"),
                    state.get("core_version"),
                )
        else:
            log.warning("Failed to fetch status from WebApi: %s", msg(rsp))

    def request(self, method: str, route: str, **kwargs: Unpack[dict]) -> Response | None:
        """Preconfigured request that handles timeouts, authentication & most common errors."""
        try:
            requests.request(
                method=method,
                url=f"{self._cfg.server}{route}",
                headers=self._auth,
                timeout=self._cfg.timeout,
                **kwargs,
            )
        except requests.Timeout:
            return None
        except requests.ConnectionError:
            return None

    @staticmethod
    def response_msg(rsp: Response) -> str:
        """"""
        try:
            return f"{rsp.reason} - {rsp.json()['detail']}"
        except JSONDecodeError:
            return f"{rsp.reason}"

    # ####################################################################
    # Content
    # ####################################################################

    def list_content_types(self) -> list[str]:
        rsp = self.request("get", "content")
        if rsp is None or not rsp.ok:
            return []
        return rsp.json()
