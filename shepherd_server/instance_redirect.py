"""
run with: uvicorn prototype_redirect:app --reload
run with: python3 ./prototype_redirect.py
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import RedirectResponse

from .config import CFG
from .version import version

app = FastAPI(
    title="shepherd-web-redirect",
    version=str(version),
    redoc_url=None,
    docs_url=None,
)


@app.get("/")
async def redir() -> RedirectResponse:
    return RedirectResponse(CFG.redirect_url)


def run() -> None:
    ssl_enabled = CFG.ssl_available()
    if ssl_enabled:
        app.add_middleware(HTTPSRedirectMiddleware)

    uvi_args = {
        "app": f"{run.__module__}:app",
        "reload": False,
        "port": 443 if ssl_enabled else 80,
        "host": CFG.root_url,
    }
    if ssl_enabled:
        uvi_args["ssl_keyfile"] = CFG.ssl_keyfile.as_posix()
        uvi_args["ssl_certfile"] = CFG.ssl_certfile.as_posix()
        uvi_args["ssl_ca_certs"] = CFG.ssl_ca_certs.as_posix()

    uvicorn.run(**uvi_args)
