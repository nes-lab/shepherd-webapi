import os
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import Self

import yaml
from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field
from pydantic import HttpUrl
from pydantic import StringConstraints
from shepherd_core import local_now
from shepherd_core import logger
from shepherd_core.data_models import Wrapper
from yaml import Node
from yaml import SafeDumper

PasswordStr = Annotated[str, StringConstraints(min_length=10, max_length=64, pattern=r"^[ -~]+$")]
# ⤷ Regex = All Printable ASCII-Characters with Space


def generate_password() -> PasswordStr:
    import exrex

    return exrex.getone("[ -~]{64}")


def generic2str(dumper: SafeDumper, data: Any) -> Node:
    """Add a yaml-representation for a specific datatype."""
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data))


yaml.add_representer(HttpUrl, generic2str, SafeDumper)


def get_xdg_config() -> Path:
    _value = os.environ.get("XDG_CONFIG_HOME")
    if _value is None or _value == "":
        return Path("~").expanduser() / ".config/"
    return Path(_value).resolve()


path_shp_config = get_xdg_config() / "shepherd/client.yaml"


class Cfg(BaseModel):
    __slots__ = ()

    server: HttpUrl = "https://shepherd.cfaed.tu-dresden.de:8000/"
    user_email: EmailStr | None = None
    password: PasswordStr | None = Field(default_factory=generate_password)

    def to_file(self) -> None:
        """Store data to yaml in a wrapper."""
        model_wrap = Wrapper(
            datatype=type(self).__name__,
            created=local_now(),
            parameters=self.model_dump(exclude_unset=True),
        )
        model_yaml = yaml.safe_dump(
            model_wrap.model_dump(exclude_unset=True, exclude_defaults=True),
            default_flow_style=False,
            sort_keys=False,
        )
        if not path_shp_config.parent.exists():
            path_shp_config.parent.mkdir(parents=True)
        with path_shp_config.open("w") as f:
            f.write(model_yaml)

    @classmethod
    def from_file(cls) -> Self:
        """Load from yaml."""
        if not path_shp_config.exists():
            logger.debug("No config found, will use default")
            return cls()
        with path_shp_config.open() as cfg_file:
            cfg_dict = yaml.safe_load(cfg_file)
        cfg_wrap = Wrapper(**cfg_dict)
        if cfg_wrap.datatype != cls.__name__:
            raise ValueError("Data in file does not match the requirement")
        return cls(**cfg_wrap.parameters)
