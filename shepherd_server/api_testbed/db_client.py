from pathlib import Path
from typing import TypedDict

from pydantic import validate_call
from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.data_models.base.wrapper import Wrapper
from typing_extensions import Self
from typing_extensions import Unpack

from shepherd_server.api_user.models import User


class DBClient:
    _instance: Self | None = None

    def __init__(self, server: str | None = None, token: str | Path | None = None) -> None:
        if server is not None:
            raise ValueError("Server not applicable for the DB-Client")
        if token is not None:
            raise ValueError("Token not applicable for the DB-Client")

    @classmethod
    def __new__(cls, *_args: tuple, **_kwargs: Unpack[TypedDict]) -> Self:
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __del__(self) -> None:
        DBClient._instance = None

    @validate_call
    def connect(self, _server: str | None = None, _token: str | Path | None = None) -> bool:
        """
        server: either "local" to use demo-fixtures or something like "https://HOST:PORT"
        token: your account validation
        """
        raise ValueError("Connection to Server not applicable here")

    def insert(self, data: ShpModel) -> bool:
        wrap = Wrapper(
            datatype=type(data).__name__,
            parameters=data.model_dump(),
        )
        if self._connected:
            r = self._req.post(self._server + "/add", data=wrap.model_dump_json(), timeout=2)
            r.raise_for_status()
        else:
            self._fixtures.insert_model(wrap)
        return True

    def query_ids(self, model_type: str) -> list:
        if self._connected:
            raise RuntimeError("Not Implemented, TODO")
        return list(self._fixtures[model_type].elements_by_id.keys())

    def query_names(self, model_type: str) -> list:
        if self._connected:
            raise RuntimeError("Not Implemented, TODO")
        return list(self._fixtures[model_type].elements_by_name.keys())

    def query_item(
        self,
        model_type: str,
        uid: int | None = None,
        name: str | None = None,
    ) -> dict:
        if self._connected:
            raise RuntimeError("Not Implemented, TODO")
        if uid is not None:
            return self._fixtures[model_type].query_id(uid)
        if name is not None:
            return self._fixtures[model_type].query_name(name)
        raise ValueError("Query needs either uid or name of object")

    def _query_session_key(self) -> bool:
        if self._server:
            r = self._req.get(self._server + "/session_key", timeout=2)
            r.raise_for_status()
            self._key = r.json()["value"]  # TODO: not finished
            return True
        return False

    def _query_user_data(self) -> bool:
        if self._server:
            r = self._req.get(self._server + "/user?token=" + self._token, timeout=2)
            # TODO: possibly a security nightmare (send via json or encrypted via public key?)
            r.raise_for_status()
            self._user = User(**r.json())
            return True
        return False

    def try_inheritance(self, model_type: str, values: dict) -> (dict, list):
        if self._connected:
            raise RuntimeError("Not Implemented, TODO")
        return self._fixtures[model_type].inheritance(values)

    def try_completing_model(self, model_type: str, values: dict) -> (dict, list):
        """Init by name/id, for none existing instances raise Exception"""
        if len(values) == 1 and next(iter(values.keys())) in {"id", "name"}:
            value = next(iter(values.values()))
            if (
                isinstance(value, str)
                and value.lower() in self._fixtures[model_type].elements_by_name
            ):
                values = self.query_item(model_type, name=value)
            elif isinstance(value, int) and value in self._fixtures[model_type].elements_by_id:
                # TODO: still depending on _fixture
                values = self.query_item(model_type, uid=value)
            else:
                msg = f"Query {model_type} by name / ID failed - {values} is unknown!"
                raise ValueError(msg)
        return self.try_inheritance(model_type, values)

    def fill_in_user_data(self, values: dict) -> dict:
        if self._user:
            # TODO: this looks wrong, should have "is None", why not always overwrite?
            if values.get("owner"):
                values["owner"] = self._user.name
            if values.get("group"):
                values["group"] = self._user.group

        # hotfix until testbed.client is working, TODO
        if values.get("owner") is None:
            values["owner"] = "unknown"
        if values.get("group") is None:
            values["group"] = "unknown"

        return values
