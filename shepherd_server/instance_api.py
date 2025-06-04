"""
Software Interface ie. shepherd_data.testbed_client

small excurse into what HTTP-Verb to use:
- create -> POST
- read -> GET
- replace -> PUT
- partial modification -> PATCH
- delete -> DELETE


"""

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.responses import FileResponse

from .api_auth.router import router as auth_router
from .api_experiment.router import router as experiment_router
from .api_user.router import router as user_router
from .config import CFG
from .instance_db import db_available
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
# app.include_router(testbed_router)
app.include_router(user_router)
app.include_router(experiment_router)


@app.get("/")
async def root() -> dict[str, str]:
    # TODO: this should probably also go into a router
    return {"message": "Hello World - from FastApi-Server-Prototype"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon1() -> FileResponse:
    return FileResponse((path_favicon / "favicon.ico").as_posix())


@app.get("/favicon.svg", include_in_schema=False)
async def favicon2() -> FileResponse:
    return FileResponse((path_favicon / "favicon.svg").as_posix())


def run() -> None:
    ssl_enabled = CFG.ssl_available()
    if ssl_enabled:
        app.add_middleware(HTTPSRedirectMiddleware)

    if not db_available(timeout=5):
        log.error("No connection to database! Will exit WebAPI now.")
        return

    uvi_args = {
        "app": f"{run.__module__}:app",
        "reload": False,
        "port": CFG.root_port,
        "host": CFG.root_url,
    }
    if ssl_enabled:
        uvi_args["ssl_keyfile"] = CFG.ssl_keyfile.as_posix()
        uvi_args["ssl_certfile"] = CFG.ssl_certfile.as_posix()
        uvi_args["ssl_ca_certs"] = CFG.ssl_ca_certs.as_posix()

    uvicorn.run(**uvi_args)
