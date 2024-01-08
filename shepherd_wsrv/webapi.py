from fastapi import FastAPI

# run with: uvicorn shepherd_wsrv.webapi:app --reload
# -> open interface http://127.0.0.1:8000
# -> open docs      http://127.0.0.1:8000/docs
# -> open docs      http://127.0.0.1:8000/redoc -> long load, but interactive / better


tag_metadata = [
    {
        "name": "emulator",
        "description": "...",
        "externalDocs": {
            "description": "**inner** workings",
            "url": "https://orgua.github.io/shepherd/user/basics.html#emulator",
        },
    },
]


app = FastAPI(
    title="shepherd-webserver",
    version="23.08.22",
    description="The web-api for the shepherd-testbed for energy harvesting CPS",
    redoc_url="/",
    # contact="https://github.com/orgua/shepherd",
    # docs_url=None,
    openapi_tags=tag_metadata,
)
