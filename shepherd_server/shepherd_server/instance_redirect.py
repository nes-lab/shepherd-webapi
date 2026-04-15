"""
run with: uvicorn prototype_redirect:app --reload
run with: python3 ./prototype_redirect.py
"""

import asyncio
from importlib import metadata

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import RedirectResponse
from shepherd_core.data_models.base.timezone import local_now

from .api_testbed.models_status import TestbedDB
from .config import server_config
from .instance_db import db_client
from .logger import log

app = FastAPI(
    title="shepherd-web-redirect",
    version=metadata.version("shepherd-server"),
    redoc_url=None,
    docs_url=None,
)


@app.get("/")
async def redir() -> RedirectResponse:
    return RedirectResponse(server_config.redirect_url)


async def update_status(*, active: bool = False) -> None:
    _client = await db_client()
    tb_ = await TestbedDB.get_one()
    tb_.redirect.activated = local_now() if active else None
    tb_.redirect.url = server_config.redirect_url
    await tb_.save_changes()


def run() -> None:
    ssl_enabled = server_config.ssl_available()
    if ssl_enabled:
        app.add_middleware(HTTPSRedirectMiddleware)

    log.info("Starting http-redirect ...")

    uvi_args = {
        "app": f"{run.__module__}:app",
        "reload": False,
        "port": 443 if ssl_enabled else 80,
        "host": server_config.root_url,
    }
    if ssl_enabled:
        uvi_args["ssl_keyfile"] = server_config.ssl_keyfile.as_posix()
        uvi_args["ssl_certfile"] = server_config.ssl_certfile.as_posix()
    asyncio.run(update_status(active=True))
    try:
        uvicorn.run(**uvi_args)
    except SystemExit:
        asyncio.run(update_status())
