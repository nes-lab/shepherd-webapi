"""A basic web-client to access testbed-related content without a login."""

import copy
from collections.abc import Collection
from importlib import metadata
from typing import Any

import requests
from pydantic import HttpUrl
from pydantic import validate_call
from requests import JSONDecodeError
from requests import Response
from shepherd_core.config import core_config
from shepherd_core.logger import increase_verbose_level
from shepherd_core.logger import log
from shepherd_core.testbed_client import AbcClient
from typing_extensions import Unpack
from typing_extensions import deprecated

from .config import ClientConfig


@deprecated("use Client.response_msg() instead")
def msg(rsp: Response) -> str:
    """"""
    try:
        return f"{rsp.reason} - {rsp.json()['detail']}"
    except JSONDecodeError:
        return f"{rsp.reason}"


class TestbedClient(AbcClient):
    @validate_call
    def __init__(self, server: HttpUrl | str | None = None, *, debug: bool = False) -> None:

        if debug:
            increase_verbose_level(3)
        self._cfg = ClientConfig.from_file()
        if server is not None:
            self._cfg.server = HttpUrl(server)
        self._auth: dict | None = None
        core_config.VALIDATE_INFRA = True
        # TODO: add server name and more from server
        self.status()
        super().__init__()

    def request(self, method: str, route: str, **kwargs: Unpack[dict]) -> Response:
        """Preconfigured request that handles timeouts, authentication & most common errors."""
        # TODO: add retries?
        url = f"{self._cfg.server}{route}"
        try:
            return requests.request(
                method=method,
                url=url,
                headers=self._auth,
                timeout=self._cfg.timeout,
                **kwargs,
            )
        except requests.Timeout:
            msg = f"Request timed out on {method}({url})"
            raise ConnectionError(msg) from None
        except requests.ConnectionError:
            msg = f"Request failed with {method}({url})"
            raise ConnectionError(msg) from None

    @staticmethod
    def _msg(rsp: Response) -> str:
        """"""
        try:
            return f"{rsp.reason} - {rsp.json()['detail']}"
        except JSONDecodeError:
            return f"{rsp.reason}"

    # ####################################################################
    # Testbed-Status
    # ####################################################################

    def status(self) -> bool:
        rsp = self.request("get", "")

        if not rsp.ok:
            log.warning("Failed to fetch status from WebApi: %s", self._msg(rsp))
            return True

        had_error = False
        state = rsp.json()
        scheduler = state.get("scheduler")
        if isinstance(scheduler, dict):
            active = scheduler.get("activated")
            if active is None:
                log.warning("Scheduler not active!")
                had_error = True
            dry_run = scheduler.get("dry_run")
            if dry_run:
                log.warning("Scheduler is running in demo-mode (dry-run)!")
                had_error = True
            targets_offline = scheduler.get("targets_offline")
            if isinstance(targets_offline, Collection) and len(targets_offline) > 0:
                log.warning("One or more targets seem to be offline: %s", targets_offline)
                had_error = True
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
        return had_error

    def testbed(self) -> str:
        rsp = self.request("get", "testbed")
        if not rsp.ok:
            msg = (f"Failed to fetch status from WebApi: {self._msg(rsp)}",)
            raise ConnectionError(msg)
        state = rsp.json()
        return state.get("name")

    def get_restrictions(self) -> list[str]:
        rsp = self.request("get", "testbed/restrictions")
        if not rsp.ok:
            log.warning("Query for restrictions failed with: %s", self._msg(rsp))
            return []
        return rsp.json()

    # ####################################################################
    # Content & Component Models
    # ####################################################################

    # TODO: rename to list_resource_types()
    def list_content_types(self) -> list[str]:
        rsp = self.request("get", "content")
        if rsp is None or not rsp.ok:
            return []
        return rsp.json()

    def list_content_ids(self, model_type: str) -> list[int]:
        rsp = self.request("get", f"content/{model_type}")
        if not rsp.ok:
            return []
        return list(rsp.json().keys())

    def list_content_names(self, model_type: str) -> list[str]:
        rsp = self.request("get", f"content/{model_type}")
        if not rsp.ok:
            return []
        return list(rsp.json().values())

    def get_content_item(
        self, model_type: str, uid: int | None = None, name: str | None = None
    ) -> dict:
        # TODO: divide into by_id and by_name?
        rsp = self.request("get", f"content/{model_type}/{uid if uid is not None else name}")
        if not rsp.ok:
            return {}
        return rsp.json()

    def _try_inheritance(
        self, model_type: str, values: dict[str, Any], chain: list[str] | None = None
    ) -> tuple[dict[str, Any], list[str]]:
        """Copy of Fixture().inheritance()."""
        if chain is None:
            chain: list[str] = []
        values = copy.copy(values)
        post_process: bool = False
        fixture_base: dict = {}
        if "inherit_from" in values:
            fixture_name = values.pop("inherit_from")
            # ⤷ will also remove entry from dict
            if "name" in values and len(chain) < 1:
                base_name = str(values.get("name"))
                if base_name in chain:
                    msg = f"Inheritance-Circle detected ({base_name} already in {chain})"
                    raise ValueError(msg)
                if base_name == fixture_name:
                    msg = f"Inheritance-Circle detected ({base_name} == {fixture_name})"
                    raise ValueError(msg)
                chain.append(base_name)
            fixture_base = copy.copy(self[fixture_name])
            log.debug("'%s' will inherit from '%s'", model_type, fixture_name)
            fixture_base["name"] = fixture_name
            chain.append(fixture_name)
            base_dict, chain = self._try_inheritance(
                model_type=model_type, values=fixture_base, chain=chain
            )
            for key, value in values.items():
                # keep previous entries
                base_dict[key] = value
            values = base_dict

        # TODO: cleanup and simplify - use fill_mode() and line up with web-interface
        elif "name" in values and str(values.get("name")).lower() in self.list_content_names(
            model_type
        ):
            fixture_name = str(values.get("name")).lower()
            fixture_base = copy.copy(self.get_content_item(model_type, name=fixture_name))
            post_process = True

        elif values.get("id") in self.list_content_ids(model_type):
            id_ = values["id"]
            fixture_base = copy.copy(self.get_content_item(model_type, uid=id_))
            post_process = True

        if post_process:
            # last two cases need
            for key, value in values.items():
                # keep previous entries
                fixture_base[key] = value
            if "inherit_from" in fixture_base:
                log.error("Inheritance on server-data should not occur!")
                # TODO: test for that?
                # as long as this key is present this will act recursively
                chain.append(fixture_base["name"])
                values, chain = self._try_inheritance(model_type, values=fixture_base, chain=chain)
            else:
                values = fixture_base

        return values, chain
