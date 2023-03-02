import json
from pathlib import Path

import requests
import yaml


def post_data(file: Path, url: str):
    print(f"Opening {file}")
    with open(file, "rb") as f:
        data = yaml.safe_load(f)
    print(f"Got: {data}")
    response = requests.post(url, json=json.dumps(data["parameters"]))
    print(response)


post_data(Path("./example_config_emulator.yml"), "http://127.0.0.1:8000/emulator_set")
# post_data(Path("./example_config_emulator.yml"), "http://127.0.0.1:8000/json_set")
