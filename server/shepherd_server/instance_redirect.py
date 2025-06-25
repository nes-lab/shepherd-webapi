"""
run with: uvicorn prototype_redirect:app --reload
run with: python3 ./prototype_redirect.py
"""

import asyncio

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import RedirectResponse
from shepherd_core import local_now

from .api_testbed.models_status import TestbedDB
from .config import config
from .instance_db import db_client
from .logger import log
from .version import version

app = FastAPI(
    title="shepherd-web-redirect",
    version=str(version),
    redoc_url=None,
    docs_url=None,
)


@app.get("/")
async def redir() -> RedirectResponse:
    return RedirectResponse(config.redirect_url)


async def update_status(*, active: bool = False) -> None:
    _client = await db_client()
    tb_ = await TestbedDB.get_one()
    tb_.redirect.activated = local_now() if active else None
    tb_.redirect.url = config.redirect_url
    await tb_.save_changes()


def run() -> None:
    ssl_enabled = config.ssl_available()
    if ssl_enabled:
        app.add_middleware(HTTPSRedirectMiddleware)

    log.info("Starting http-redirect ...")

    uvi_args = {
        "app": f"{run.__module__}:app",
        "reload": False,
        "port": 443 if ssl_enabled else 80,
        "host": config.root_url,
    }
    if ssl_enabled:
        uvi_args["ssl_keyfile"] = config.ssl_keyfile.as_posix()
        uvi_args["ssl_certfile"] = config.ssl_certfile.as_posix()
        if config.ssl_ca_certs.exists():
            uvi_args["ssl_ca_certs"] = config.ssl_ca_certs.as_posix()
    asyncio.run(update_status(active=True))
    try:
        uvicorn.run(**uvi_args)
    except SystemExit:
        asyncio.run(update_status())
