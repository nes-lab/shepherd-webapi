import uvicorn
from fastapi import FastAPI
from fastapi import Form
from fastapi import HTTPException
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.security import OAuth2PasswordBearer
from shepherd_core.data_models import Wrapper
from shepherd_core.data_models import content as shp_cnt
from shepherd_core.data_models import testbed as shp_tb
from shepherd_core.testbed_client import tb_client

# from fastapi import Form

# imports indirectly needed: uvicorn, python-multipart, jinja2
# run with: uvicorn prototype_server:app --reload
# -> open interface http://127.0.0.1:8000
# -> open docs      http://127.0.0.1:8000/docs
# -> open docs      http://127.0.0.1:8000/redoc -> long load, but interactive / better

use_ssl = True

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
    title="shepherd-api",
    version="2023.09.21",
    description="The web-api for the shepherd-testbed for energy harvesting CPS",
    redoc_url="/",
    # contact="https://github.com/orgua/shepherd",
    # docs_url=None,
    openapi_tags=tag_metadata,
)

if use_ssl:
    app.add_middleware(HTTPSRedirectMiddleware)

# @app.get("/")
# async def root():
#    return {"message": "Hello World - from FastApi-Server-Prototype"}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


@app.post("/login")
async def login(username: str = Form(), password: str = Form()):
    return {"username": username}


# white-list for data-models
# TODO: implement a generator -> nicer documentation needed
name2model = {
    # testbed-components
    "Cape": shp_tb.Cape,
    "GPIO": shp_tb.GPIO,
    "MCU": shp_tb.MCU,
    "Observer": shp_tb.Observer,
    "Target": shp_tb.Target,
    "Testbed": shp_tb.Testbed,
    # content
    "EnergyEnvironment": shp_cnt.EnergyEnvironment,
    "Firmware": shp_cnt.Firmware,
    "VirtualHarvesterConfig": shp_cnt.VirtualHarvesterConfig,
    "VirtualSourceConfig": shp_cnt.VirtualSourceConfig,
}


@app.get("/shepherd/session_key")
async def read_session_key():
    # TODO
    return {"value": b"this_will_be_a_asym_pubkey"}


@app.get("/shepherd/uuuser")
async def read_userdata(token: str):
    # TODO
    return {
        "name": "Klaus",
        "group": "TU Dresden",
        "email": "test@best.com",
        "token": token,
    }


@app.get("/shepherd/{type_name}/ids")  # items?skip=10&limit=100
async def read_item_ids_list(type_name: str, skip: int = 0, limit: int = 40):
    if type_name not in name2model:
        raise HTTPException(status_code=404, detail="item-name not found")
    elems = tb_client.query_ids(type_name)
    return {"message": elems[skip : skip + limit]}


@app.get("/shepherd/{type_name}/names")  # items?skip=10&limit=100
async def read_item_names_list(type_name: str, skip: int = 0, limit: int = 40):
    if type_name not in name2model:
        raise HTTPException(status_code=404, detail="item-name not found")
    elems = tb_client.query_names(type_name)
    return {"message": list(elems)[skip : skip + limit]}


@app.get("/shepherd/{type_name}/item")
async def read_item_by_id(
    type_name: str,
    item_id: int | None = None,
    item_name: str | None = None,
):
    if type_name not in name2model:
        raise HTTPException(status_code=404, detail="item-name not found")

    if item_id:
        try:
            return name2model[type_name](id=item_id).dict()
        except ValueError:
            raise HTTPException(status_code=404, detail="item-id not found")

    elif item_name:
        try:
            return name2model[type_name](name=item_name).dict()
        except ValueError:
            raise HTTPException(status_code=404, detail="item-name not found")

    raise HTTPException(status_code=404, detail="neither item-id or -name provided")


@app.post("/shepherd/{type_name}/add")
async def write_item(type_name: str, item: Wrapper):
    pass


if __name__ == "__main__":
    uvi_args = {
        "app": "prototype_server:app",
        "reload": False,
        "port": 8000,
        "host": "shepherd.cfaed.tu-dresden.de",
    }
    if use_ssl:
        uvi_args["ssl_keyfile"] = "/etc/shepherd/ssl_private_key.pem"
        uvi_args["ssl_certfile"] = "/etc/shepherd/ssl_certificate.pem"
        uvi_args["ssl_ca_certs"] = "/etc/shepherd/ssl_ca_certs.pem"

    uvicorn.run(**uvi_args)

"""

@app.post("/emulator_set", tags=["emulator"])
async def set_emulator(item: Emulator):
    # async def set_emulator(item: Emulator, token: str = Depends(oauth2_scheme)):
    if isinstance(item, dict):
        print(f"Emulator had to be casted from dict")
        item = Emulator.parse_obj(item)
    print(f"Received new emulator - ipath = '{item.input_path}'")
    return {"status": "SUCCESS", "data": item.dict()}


@app.post("/json_set")
async def set_json(data: Wrapper):
    if isinstance(data, dict):
        data = Emulator.parse_obj(data)
    getattr("models", data.type).parse_obj(data.parameters)
    # item = await data.json()
    print(f"Received new json {data}")
    item = Emulator.parse_obj(data)  # TODO: dynamic casting would be needed
    return {"status": "SUCCESS", "data": item.dict()}


@app.post("/virtualSource_set")
async def set_virtual_source(item: VirtualSource):
    print(f"Received new VirtualSource - name = '{item.name}'")
    return item.dict()


@app.post("/virtualHarvester_set")
async def set_virtual_harvester(item: VirtualHarvester):
    print(f"Received new VirtualHarvester - name = '{item.name}'")
    return item.dict()


@app.get("/virtualHarvester_items")
async def read_virtual_harvester_items(skip: int = 0, limit: int = 40):
    print(f"Request for VirtualHarvester [{skip} : {skip + limit}]")
    return {"message": list(vharvesters.keys())[skip: skip + limit]}


@app.get("/virtualHarvester_item/{item_id}")
async def read_virtual_harvester_item(item_id: str):
    print(f"Request for VirtualHarvester [{item_id}]")
    return VirtualSource(name=item_id).dict()

"""
