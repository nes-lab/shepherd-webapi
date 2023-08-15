import json
from datetime import datetime
from datetime import timedelta

import requests
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from shepherd_core.data_models import EnergyEnvironment
from shepherd_core.data_models import Experiment
from shepherd_core.data_models import Firmware
from shepherd_core.data_models import PowerTracing
from shepherd_core.data_models import TargetConfig
from shepherd_core.data_models import VirtualHarvesterConfig
from shepherd_core.data_models import VirtualSourceConfig
from shepherd_core.data_models.testbed import Testbed

do_send_power = False
do_send_exper = False
do_recv_testb = True


def post_data(mdata: BaseModel, url: str):
    # things to consider:
    # data.dict()               has trouble with special type like Path, datetime
    # jsonable_encoder(data)    fastapi receives dict instead of Baseclass
    # data.json()               fastapi does fail to parse at all
    #                           different parser like orjson also fails
    print(f"Will post: {mdata.dict()}")
    response = requests.post(url, json=jsonable_encoder(mdata))
    print(response)


def get_data(url: str):
    return requests.get(
        url,
    )


hrv = VirtualHarvesterConfig(name="mppt_bq_thermoelectric")

target_cfgs = [
    # first init similar to yaml
    TargetConfig(
        target_IDs=list(range(3001, 3004)),
        custom_IDs=list(range(0, 3)),
        energy_env={"name": "SolarSunny"},
        virtual_source={"name": "diode+capacitor"},
        firmware1={"name": "nrf52_demo_rf"},
    ),
    # second Instance fully object-oriented
    TargetConfig(
        target_IDs=list(range(2001, 2005)),
        custom_IDs=list(range(7, 18)),
        energy_env=EnergyEnvironment(name="ThermoelectricWashingMachine"),
        virtual_source=VirtualSourceConfig(name="BQ25570-Schmitt", harvester=hrv),
        firmware1=Firmware(name="nrf52_demo_rf"),
        firmware2=Firmware(name="msp430_deep_sleep"),
    ),
]

xperi = Experiment(
    id="4567",
    name="meaningful Test-Name",
    time_start=datetime.utcnow() + timedelta(minutes=30),
    target_configs=target_cfgs,
)


if do_send_exper:
    post_data(xperi, "http://127.0.0.1:8000/emulator_set")
    # post_data(data, "http://127.0.0.1:8000/json_set")

if do_send_power:
    post_data(PowerTracing(), "http://127.0.0.1:8000/feature_PowerLogging_set")

if do_recv_testb:
    resp = get_data("http://127.0.0.1:8000/testbed/1337")
    data = json.loads(resp.text)
    tb = Testbed(**data)
    print(tb.name)
