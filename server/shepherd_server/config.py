import os
from datetime import timedelta
from pathlib import Path

from decouple import config as dcoup_cfg
from pydantic import BaseModel
from pydantic import PositiveInt

from .logger import log


def _get_xdg_path(variable_name: str, default: str) -> Path:
    _value = os.environ.get(variable_name)
    if _value is None or _value == "":
        return Path("~").expanduser() / default
    return Path(_value)


PATH_XDG_CONFIG = _get_xdg_path("XDG_CONFIG_HOME", ".config/")


class ConfigDefault(BaseModel):
    __slots__ = ()
    # web related
    root_url: str = dcoup_cfg("ROOT_URL", default="127.0.0.1")
    root_port: int = 8000
    testbed_name: str = dcoup_cfg("TESTBED_NAME", default="unit_testing_testbed")

    contact: dict = {
        "name": "Ingmar Splitt",
        "url": "https://github.com/nes-lab/shepherd",
        "email": "ingmar.splitt@tu-dresden.de",
    }
    ssl_keyfile: Path = dcoup_cfg(
        "SSL_KEYFILE", default=PATH_XDG_CONFIG / "shepherd/ssl_private_key.pem"
    )
    ssl_certfile: Path = dcoup_cfg(
        "SSL_CERTFILE", default=PATH_XDG_CONFIG / "shepherd/ssl_certificate.pem"
    )
    # ca_certs seems to be optional
    ssl_ca_certs: Path = dcoup_cfg(
        "SSL_CA_CERTS", default=PATH_XDG_CONFIG / "shepherd/ssl_ca_certs.pem"
    )
    # user auth
    auth_salt: bytes = dcoup_cfg("AUTH_SALT").encode("UTF-8")
    secret_key: str = dcoup_cfg("SECRET_KEY", default="replace me")
    # will raise if missing default, TODO: remove default

    # api redirect
    redirect_url: str = "https://nes-lab.github.io/shepherd-nova/"

    # MAIL
    mail_enabled: bool = dcoup_cfg("MAIL_ENABLED", default=False, cast=bool)
    mail_server: str = dcoup_cfg("MAIL_SERVER", default="mail.your-server.de")
    mail_port: int = dcoup_cfg("MAIL_PORT", default=465, cast=int)
    mail_username: str = dcoup_cfg("MAIL_USERNAME", default="")
    mail_password: str = dcoup_cfg("MAIL_PASSWORD", default="")
    mail_sender: str = dcoup_cfg("MAIL_SENDER", default="")
    mail_sender_name: str = dcoup_cfg("MAIL_SENDER_NAME", default="Shepherd Testbed")

    # Quotas for users
    quota_default_duration: timedelta = timedelta(minutes=60)
    quota_default_storage: PositiveInt = 200 * (10**9)
    # 20 nodes @  4 h are ~  290 GB
    # 30 nodes @ 10 h are ~ 1080 GB

    # Lifetime of Objects
    age_max_user: timedelta = timedelta(days=18 * 31)
    age_max_experiment: timedelta = timedelta(days=6 * 31)
    age_min_experiment: timedelta = timedelta(days=15)

    def ssl_available(self) -> bool:
        _files = (self.ssl_keyfile, self.ssl_certfile)  # out: self.ssl_ca_certs
        _avail = all(_p.exists() for _p in _files)
        if _avail:
            log.info("SSL available, as keys & certs were found")
        else:
            log.warning("SSL disabled!")
            for _file in _files:
                if not _file.exists():
                    log.warning(" -> NOT FOUND: %s", _file.as_posix())
        return _avail

    def server_url(self) -> str:
        return f"http{'s' if self.ssl_available() else ''}://{self.root_url}:{self.root_port}"


config = ConfigDefault()
