from fastapi import HTTPException
from typing import Optional

from fastapi import Depends
from fastapi import FastAPI
from fastapi import Form
from fastapi.security import OAuth2PasswordBearer
import shepherd_core.data_models.testbed as stb
import shepherd_core.data_models.content as scn
from shepherd_core.data_models.content.firmware import fixtures as fix_fw
from shepherd_core.data_models.content.energy_environment import fixtures as fix_eenv
from shepherd_core.data_models.content.virtual_source import fixtures as fix_vsrc
from shepherd_core.data_models.content.virtual_harvester import fixtures as fix_vhrv
from shepherd_core.data_models.testbed.cape import fixtures as fix_cape
from shepherd_core.data_models.testbed.mcu import fixtures as fix_mcu
from shepherd_core.data_models.testbed.gpio import fixtures as fix_gpio
from shepherd_core.data_models.testbed.observer import fixtures as fix_observer
from shepherd_core.data_models.testbed.target import fixtures as fix_target
from shepherd_core.data_models.testbed.testbed import fixtures as fix_testbed

# from fastapi import Form

# imports indirectly needed: uvicorn, python-multipart, jinja2
# run with: uvicorn prototype_server:app --reload
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
    }
]


app = FastAPI(
    title="shepherd-api",
    version="22.03.03",
    description="The web-api for the shepherd-testbed for energy harvesting CPS",
    redoc_url="/",
    # contact="https://github.com/orgua/shepherd",
    # docs_url=None,
    openapi_tags=tag_metadata,
)

# @app.get("/")
# async def root():
#    return {"message": "Hello World - from FastApi-Server-Prototype"}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


@app.post("/login")
async def login(username: str = Form(), password: str = Form()):
    return {"username": username}


interface_items = {
    # components
    "cape": {"model": stb.Cape, "db": fix_cape},
    "gpio": {"model": stb.GPIO, "db": fix_gpio},
    "mcu": {"model": stb.MCU, "db": fix_mcu},
    "observer": {"model": stb.Observer, "db": fix_observer},
    "target": {"model": stb.Target, "db": fix_target},
    "testbed": {"model": stb.Testbed, "db": fix_testbed},
    # content
    "energy_environment": {"model": scn.EnergyEnvironment, "db": fix_eenv},
    "firmware": {"model": scn.Firmware, "db": fix_fw},
    "virtual_harvester": {"model": scn.virtual_harvester, "db": fix_vhrv},
    "virtual_source": {"model": scn.virtual_source, "db": fix_vsrc},
}


@app.get("/shepherd/{item_name}")  # items?skip=10&limit=100
async def read_item_ids_list(item_name: str, skip: int = 0, limit: int = 40):
    if item_name not in interface_items:
        raise HTTPException(status_code=404, detail="item-name not found")
    elems = interface_items[item_name]["db"].elements_by_id.keys()
    return {"message": list(elems)[skip : skip + limit]}


@app.get("/shepherd/{item_name}/{item_id}")
async def read_item_by_id(item_name: str, item_id: Optional[int]):
    if item_name not in interface_items:
        raise HTTPException(status_code=404, detail="item-name not found")
    interface = interface_items[item_name]
    if item_id not in interface["db"].elements_by_id:
        raise HTTPException(status_code=404, detail="item-id not found")
    return interface["model"](id=item_id).dict()


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
