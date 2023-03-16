from fastapi import Depends
from fastapi import FastAPI
from fastapi import Form
from fastapi.security import OAuth2PasswordBearer
from models.interface_emulator import Emulator
from models.interface_features import GpioLogging
from models.interface_features import PowerLogging
from models.interface_features import SystemLogging
from models.model_virtualHarvester import VirtualHarvester
from models.model_virtualHarvester import vharvesters

# from fastapi import Form
from models.model_virtualSource import VirtualSource
from models.model_virtualSource import vsources
from models.model_wrapper import Wrapper

# imports indirectly needed: uvicorn, python-multipart, jinja2
# run with: uvicorn prototype_server:app --reload
# -> open interface http://127.0.0.1:8000
# -> open docs      http://127.0.0.1:8000/docs
# -> open docs      http://127.0.0.1:8000/redoc -> long load, but interactive / better

tag_metadata = [
    {"name": "emulator",
     "description": "...",
     "externalDocs": {
         "description": "**inner** workings",
         "url": "https://orgua.github.io/shepherd/user/basics.html#emulator",
     }
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


@app.get("/virtualSource_items")  # items?skip=10&limit=100
async def read_virtual_source_items(skip: int = 0, limit: int = 40):
    print(f"Request for VirtualSource [{skip} : {skip + limit}]")
    return {"message": list(vsources.keys())[skip: skip + limit]}


@app.get("/virtualSource_item/{item_id}")
async def read_virtual_source_item(item_id: str):
    print(f"Request for VirtualSource [{item_id}]")
    return VirtualSource(name=item_id).dict()


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


@app.post("/feature_PowerLogging_set")
async def set_feature_power_logging(item: PowerLogging):
    print(
        f"Received new PowerLogging - log V/C = '{item.log_voltage, item.log_current}'",
    )
    return item.dict()


@app.post("/feature_GpioLogging_set")
async def set_feature_gpio_logging(item: GpioLogging):
    print(f"Received new GpioLogging - log gpio = '{item.log_gpio}'")
    return item.dict()


@app.post("/feature_SystemLogging_set")
async def set_feature_system_logging(item: SystemLogging):
    print(
        f"Received new SystemLogging - log dmesg/ptp = '{item.log_dmesg, item.log_ptp}'",
    )
    return item.dict()
