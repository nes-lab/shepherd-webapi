from pydantic import HttpUrl
from pydantic import validate_call

from .config import Cfg

# TODO: this holds all FN to load testbed-related content (without login)


class WebClient:
    @validate_call
    def __init__(self, server: HttpUrl | None = None) -> None:
        if not hasattr(self, "_cfg"):
            self._cfg = Cfg()
        if server is not None:
            self._cfg.server = server
