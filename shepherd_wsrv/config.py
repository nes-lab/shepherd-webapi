from decouple import config
from pathlib import Path

from pydantic import BaseModel


class Cfg(BaseModel):
    __slots__ = ()
    # web related
    host_url: str = config("HOST_URL", default="127.0.0.1")
    # "shepherd.cfaed.tu-dresden.de"
    contact: dict = {
                "name": "Ingmar Splitt",
                "url": "https://github.com/orgua/shepherd",
                "email": "ingmar.splitt@tu-dresden.de",
    }
    ssl_enabled: bool = False
    ssl_keyfile: Path = Path("/etc/shepherd/ssl_private_key.pem")
    ssl_certfile: Path = Path("/etc/shepherd/ssl_certificate.pem")
    ssl_ca_certs: Path = Path("/etc/shepherd/ssl_ca_certs.pem")
    # api redirect
    redirect_url: str = "https://orgua.github.io/shepherd/external/testbed.html"


CFG = Cfg()
# TODO: disable ssl if files not found, warn about it
