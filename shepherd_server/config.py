import os
from datetime import timedelta
from pathlib import Path

from decouple import config
from pydantic import BaseModel

from shepherd_server.logger import log


def _get_xdg_path(variable_name: str, default: str) -> Path:
    _value = os.environ.get(variable_name)
    if _value is None or _value == "":
        return Path("~").expanduser() / default
    return Path(_value)


PATH_XDG_CONFIG = _get_xdg_path("XDG_CONFIG_HOME", ".config/")


class Cfg(BaseModel):
    __slots__ = ()
    # web related
    root_url: str = config("ROOT_URL", default="127.0.0.1")
    # "shepherd.cfaed.tu-dresden.de"
    contact: dict = {
        "name": "Ingmar Splitt",
        "url": "https://github.com/nes-lab/shepherd",
        "email": "ingmar.splitt@tu-dresden.de",
    }
    ssl_keyfile: Path = PATH_XDG_CONFIG / "shepherd/ssl_private_key.pem"
    ssl_certfile: Path = PATH_XDG_CONFIG / "shepherd/ssl_certificate.pem"
    ssl_ca_certs: Path = PATH_XDG_CONFIG / "shepherd/ssl_ca_certs.pem"
    # user auth
    auth_salt: bytes = config("SALT", default="and_pepper").encode("UTF-8")
    secret_key: str = config("SECRET_KEY", default="replace me")
    # will raise if missing default, TODO: remove default

    # api redirect
    redirect_url: str = "https://nes-lab.github.io/shepherd-nova/"

    # MAIL
    mail_console: bool = config("MAIL_CONSOLE", default=False, cast=bool)
    mail_server: str = config("MAIL_SERVER", default="mail.your-server.de")
    mail_port: int = config("MAIL_PORT", default=993, cast=int)
    mail_username: str = config("MAIL_USERNAME", default="")
    mail_password: str = config("MAIL_PASSWORD", default="")
    mail_sender: str = config("MAIL_SENDER", default="testbed@nes-lab.org")

    # Quotas for users
    quota_default_duration: timedelta = timedelta(minutes=60)
    quota_default_storage: int = 200 * (10**9)
    # 20 nodes @  4 h are ~  290 GB
    # 30 nodes @ 10 h are ~ 1080 GB
    # TODO: add temporary quota relief?

    def ssl_available(self) -> bool:
        _files = (self.ssl_keyfile, self.ssl_certfile, self.ssl_ca_certs)
        _avail = all(_p.exists() for _p in _files)
        if _avail:
            log.info("SSL available, as keys & certs were found")
        else:
            log.warning("SSL disabled!")
            for _file in _files:
                if not _file.exists():
                    log.warning(" -> NOT FOUND: %s", _file.as_posix())
        return _avail


CFG = Cfg()
