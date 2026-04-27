import os
from pathlib import Path
from typing import Annotated

import ryaml
from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field
from pydantic import HttpUrl
from pydantic import StringConstraints
from shepherd_core.data_models.base.timezone import local_now
from shepherd_core.data_models.base.wrapper import Wrapper
from shepherd_core.logger import log
from typing_extensions import Self

PasswordStr = Annotated[str, StringConstraints(min_length=10, max_length=64, pattern=r"^[ -~]+$")]
# ⤷ Regex = All Printable ASCII-Characters with Space


def generate_password() -> PasswordStr:
    import exrex

    return exrex.getone("[ -~]{64}")


def get_xdg_config() -> Path:
    _value = os.environ.get("XDG_CONFIG_HOME")
    if _value is None or _value == "":
        return Path("~").expanduser() / ".config/"
    return Path(_value).resolve()


server_default = HttpUrl("https://shepherd.cfaed.tu-dresden.de:8000")
# TODO: pull directly from coreConfig


class ClientConfig(BaseModel):
    __slots__ = ()

    server: HttpUrl = server_default
    """ ⤷ note that '/' at the end is needed and automatically added when casting to HttpUrl."""
    account_email: EmailStr | None = None
    password: PasswordStr | None = Field(default_factory=generate_password)
    timeout: int = 3

    def to_file(self) -> None:
        """Store data to YAML in a wrapper."""
        model_wrap = Wrapper(
            datatype=type(self).__name__,
            created=local_now(),
            parameters=self.model_dump(exclude_unset=True),
        ).model_dump(exclude_unset=True, exclude_defaults=True)
        config_path = self.file_path()
        if not config_path.parent.exists():
            config_path.parent.mkdir(parents=True)
        with config_path.open("w", encoding="utf-8") as cfg_file:
            ryaml.dump(cfg_file, model_wrap)

    @classmethod
    def from_file(cls) -> Self:
        """Load from YAML."""
        config_path = cls.file_path()
        if not config_path.exists():
            log.debug("No config found, will use default")
            return cls()
        with config_path.open(encoding="utf-8") as cfg_file:
            cfg_dict = ryaml.load(cfg_file)
        cfg_wrap = Wrapper(**cfg_dict)
        if cfg_wrap.datatype not in {cls.__name__, "Config"}:
            raise ValueError("Data in file does not match the requirement")
        return cls(**cfg_wrap.parameters)

    @classmethod
    def file_path(cls) -> Path:
        return get_xdg_config() / "shepherd/client.yaml"

    @classmethod
    def backup(cls) -> bool:
        path_config = cls.file_path()
        if path_config.exists():
            path_config.rename(path_config.with_suffix(f".backup_{local_now().isoformat()}"))
            return True
        return False
