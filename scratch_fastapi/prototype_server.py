from typing import Optional

from fastapi import Depends
from fastapi import FastAPI
from fastapi import Form
from fastapi.security import OAuth2PasswordBearer
import shepherd_core.data_models.testbed as stb
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
"""


@app.get("/cape")  # items?skip=10&limit=100
async def read_cape_items(skip: int = 0, limit: int = 40):
    print(f"Request for Capes [{skip} : {skip + limit}]")
    return {"message": list(fix_cape.elements_by_id.keys())[skip : skip + limit]}


@app.get("/cape/{item_id}")
async def read_cape_item(item_id: Optional[int]):
    print(f"Request for Capes [{item_id}]")
    if item_id not in fix_cape.elements_by_id:
        return None
    return stb.Cape(id=item_id).dict()


@app.get("/gpio")  # items?skip=10&limit=100
async def read_gpio_items(skip: int = 0, limit: int = 40):
    print(f"Request for gpio [{skip} : {skip + limit}]")
    return {"message": list(fix_gpio.elements_by_id.keys())[skip : skip + limit]}


@app.get("/gpio/{item_id}")
async def read_gpio_item(item_id: Optional[int]):
    print(f"Request for gpio [{item_id}]")
    if item_id not in fix_gpio.elements_by_id:
        return None
    return stb.GPIO(id=item_id).dict()


@app.get("/mcu")  # items?skip=10&limit=100
async def read_mcu_items(skip: int = 0, limit: int = 40):
    print(f"Request for mcu [{skip} : {skip + limit}]")
    return {"message": list(fix_mcu.elements_by_id.keys())[skip : skip + limit]}


@app.get("/mcu/{item_id}")
async def read_mcu_item(item_id: Optional[int]):
    print(f"Request for mcu [{item_id}]")
    if item_id not in fix_mcu.elements_by_id:
        return None
    return stb.MCU(id=item_id).dict()


@app.get("/observer")  # items?skip=10&limit=100
async def read_observer_items(skip: int = 0, limit: int = 40):
    print(f"Request for observer [{skip} : {skip + limit}]")
    return {"message": list(fix_observer.elements_by_id.keys())[skip : skip + limit]}


@app.get("/observer/{item_id}")
async def read_observer_item(item_id: Optional[int]):
    print(f"Request for observer [{item_id}]")
    if item_id not in fix_observer.elements_by_id:
        return None
    return stb.Observer(id=item_id).dict()


@app.get("/target")  # items?skip=10&limit=100
async def read_target_items(skip: int = 0, limit: int = 40):
    print(f"Request for target [{skip} : {skip + limit}]")
    return {"message": list(fix_target.elements_by_id.keys())[skip : skip + limit]}


@app.get("/target/{item_id}")
async def read_target_item(item_id: Optional[int]):
    print(f"Request for target [{item_id}]")
    if item_id not in fix_target.elements_by_id:
        return None
    return stb.Target(id=item_id).dict()


@app.get("/testbed")  # items?skip=10&limit=100
async def read_testbed_items(skip: int = 0, limit: int = 40):
    print(f"Request for testbed [{skip} : {skip + limit}]")
    return {"message": list(fix_testbed.elements_by_id.keys())[skip : skip + limit]}


@app.get("/testbed/{item_id}")
async def read_testbed_item(item_id: Optional[int]):
    print(f"Request for testbed [{item_id}]")
    if item_id not in fix_testbed.elements_by_id:
        return None
    return stb.Testbed(id=item_id).dict()


"""

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
