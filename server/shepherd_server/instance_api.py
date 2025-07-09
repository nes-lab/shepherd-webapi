"""
Software Interface ie. shepherd_data.testbed_client

small excurse into what HTTP-Verb to use:
- create -> POST
- read -> GET
- replace -> PUT
- partial modification -> PATCH
- delete -> DELETE


"""

import asyncio
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from shepherd_core import local_now
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.responses import FileResponse

from .api_auth.router import router as auth_router
from .api_experiment.router import router as experiment_router
from .api_testbed.models_status import TestbedDB
from .api_testbed.models_status import TestbedStatus
from .api_testbed.router import router as testbed_router
from .api_user.router import router as user_router
from .config import config
from .instance_db import db_available
from .instance_db import db_client
from .instance_db import db_context
from .logger import log
from .version import version

# run with: uvicorn shepherd_server.webapi:app --reload
# -> open interface http://127.0.0.1:8000
# -> open docs      http://127.0.0.1:8000/docs
# -> open docs      http://127.0.0.1:8000/redoc -> long load, but interactive / better

path_favicon = Path(__file__).parent / "favicon/"

tag_metadata = [
    {
        "name": "emulator",
        "description": "...",
        "externalDocs": {
            "description": "**inner** workings to interface the testbed",
            "url": "https://nes-lab.github.io/shepherd/user/basics.html#emulator",
        },
    },
]


app = FastAPI(
    title="shepherd-webapi",
    version=str(version),
    description="The WebAPI for the shepherd-testbed for energy harvesting CPS",
    redoc_url="/doc",
    # contact="https://github.com/nes-lab/shepherd",
    docs_url="/doc0",  # this one allows login
    openapi_tags=tag_metadata,
    lifespan=db_context,
)

# TODO: probably not needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(user_router)
app.include_router(experiment_router)
app.include_router(testbed_router)


@app.get("/")
async def root() -> TestbedStatus:
    # TODO: this should probably also go into a router
    return await TestbedDB.get_one()


@app.get("/favicon.ico", include_in_schema=False)
async def favicon1() -> FileResponse:
    return FileResponse((path_favicon / "favicon.ico").as_posix())


@app.get("/favicon.svg", include_in_schema=False)
async def favicon2() -> FileResponse:
    return FileResponse((path_favicon / "favicon.svg").as_posix())


async def update_status() -> None:
    from shepherd_core.version import version as core_version
    from shepherd_herd import __version__ as herd_version

    from .version import version as server_version

    _client = await db_client()
    tb_ = await TestbedDB.get_one()
    tb_.webapi.activated = local_now()
    tb_.server_version = server_version
    tb_.core_version = core_version
    tb_.herd_version = herd_version
    await tb_.save_changes()


def run() -> None:
    ssl_enabled = config.ssl_available()
    if ssl_enabled:
        app.add_middleware(HTTPSRedirectMiddleware)

    if not db_available(timeout=5):
        log.error("No connection to database! Will exit WebAPI now.")
        return

    log.info("Starting Web-Api server...")

    uvi_args = {
        "app": f"{run.__module__}:app",
        "reload": False,
        "port": config.root_port,
        "host": config.root_url,
        # TODO: add resource limits - https://www.uvicorn.org/settings/#resource-limits
    }
    if ssl_enabled:
        uvi_args["ssl_keyfile"] = config.ssl_keyfile.as_posix()
        uvi_args["ssl_certfile"] = config.ssl_certfile.as_posix()
        if isinstance(config.ssl_ca_certs, Path) and config.ssl_ca_certs.exists():
            uvi_args["ssl_ca_certs"] = config.ssl_ca_certs.as_posix()
    asyncio.run(update_status())
    uvicorn.run(**uvi_args)
