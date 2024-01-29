"""
Software Interface ie. shepherd_data.testbed_client

small excurse into what HTTP-Verb to use:
- create -> POST
- read -> GET
- replace -> PUT
- partial modification -> PATCH
- delete -> DELETE


"""
import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

from .api_auth import router as auth_router

# from .routes.mail import router as MailRouter
# from .routes.register import router as RegisterRouter
from .api_user import router as user_router
from .config import CFG
from .db_instance import db_context
from .routes.product import router as product_router
from .version import __version__

# run with: uvicorn shepherd_wsrv.webapi:app --reload
# -> open interface http://127.0.0.1:8000
# -> open docs      http://127.0.0.1:8000/docs
# -> open docs      http://127.0.0.1:8000/redoc -> long load, but interactive / better


tag_metadata = [
    {
        "name": "emulator",
        "description": "...",
        "externalDocs": {
            "description": "**inner** workings to interface the testbed",
            "url": "https://orgua.github.io/shepherd/user/basics.html#emulator",
        },
    },
]


app = FastAPI(
    title="shepherd-api",
    version=str(__version__),
    description="The web-api for the shepherd-testbed for energy harvesting CPS",
    redoc_url="/doc",
    # contact="https://github.com/orgua/shepherd",
    docs_url="/doc0",  # None,  # this one allows login
    openapi_tags=tag_metadata,
    lifespan=db_context,
)


if CFG.ssl_enabled:
    app.add_middleware(HTTPSRedirectMiddleware)


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
app.include_router(product_router)


@app.get("/")
async def root():
    # TODO: this should probably also go into a router
    return {"message": "Hello World - from FastApi-Server-Prototype"}


def run() -> None:
    uvi_args = {
        "app": f"{run.__module__}:app",
        "reload": False,
        "port": 8000,
        "host": CFG.root_url,
    }
    if CFG.ssl_enabled:
        uvi_args["ssl_keyfile"] = CFG.ssl_keyfile.as_posix()
        uvi_args["ssl_certfile"] = CFG.ssl_certfile.as_posix()
        uvi_args["ssl_ca_certs"] = CFG.ssl_ca_certs.as_posix()

    uvicorn.run(**uvi_args)
