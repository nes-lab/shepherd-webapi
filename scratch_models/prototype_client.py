import json
from pathlib import Path
from pydantic import BaseModel
from models.interface_features import PowerLogging
import requests
import yaml

from models.interface_emulator import EmulatorIF


def load_yam(file: Path) -> dict:
    print(f"Opening {file}")
    with open(file, "rb") as f:
        content = yaml.safe_load(f)
    return content


def post_data(mdata: BaseModel, url: str):
    print(f"Will post: {mdata}")
    response = requests.post(url, json=mdata.dict())
    print(response)


if False:
    data = EmulatorIF.parse_obj(load_yam(Path("./example_config_emulator.yml"))["parameters"])
    # post_data(data, "http://127.0.0.1:8000/emulator_set")
    post_data(data, "http://127.0.0.1:8000/json_set")

data = PowerLogging.parse_obj(load_yam(Path("./example_config_emulator.yml"))["parameters"]["power_logging"])
post_data(data, "http://127.0.0.1:8000/feature_PowerLogging_set")
