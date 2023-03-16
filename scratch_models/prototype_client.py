import json
from pathlib import Path

import requests
import yaml
from fastapi.encoders import jsonable_encoder
from models.interface_emulator import Emulator
from models.interface_features import PowerLogging
from pydantic import BaseModel

do_send_powerlog = True
do_send_emulator = True


def load_yam(file: Path) -> dict:
    print(f"Opening {file}")
    with open(file, "rb") as f:
        content = yaml.safe_load(f)
    return content


def post_data(mdata: BaseModel, url: str):
    # things to consider:
    # data.dict()               has trouble with special type like Path, datetime
    # jsonable_encoder(data)    fastapi receives dict instead of Baseclass
    # data.json()               fastapi does fail to parse at all
    #                           different parser like orjson also fails
    print(f"Will post: {mdata.dict()}")
    response = requests.post(url, json=jsonable_encoder(mdata))
    print(response)


if do_send_emulator:
    data = Emulator.parse_obj(
        load_yam(Path("./example_config_emulator.yml"))["parameters"],
    )
    post_data(data, "http://127.0.0.1:8000/emulator_set")
    # post_data(data, "http://127.0.0.1:8000/json_set")

if do_send_powerlog:
    data = PowerLogging.parse_obj(
        load_yam(Path("./example_config_emulator.yml"))["parameters"]["power_logging"],
    )
    post_data(data, "http://127.0.0.1:8000/feature_PowerLogging_set")
