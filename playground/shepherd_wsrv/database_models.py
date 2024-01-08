from shepherd_core.data_models.content import EnergyEnvironment as EnergyEnvironmentCore
from shepherd_core.data_models.content import VirtualHarvesterConfig as VirtualHarvesterConfigCore
from shepherd_core.data_models.content import VirtualSourceConfig as VirtualSourceConfigCore
from shepherd_core.data_models.testbed import GPIO as GPIOCore
from shepherd_core.data_models.testbed import MCU as MCUCore
from shepherd_core.data_models.testbed import Observer as ObserverCore
from shepherd_core.data_models.testbed import Testbed as TestbedCore
from shepherd_core.testbed_client import tb_client

from .database_instance import db

# ########################  CONTENT #################
# TODO: Try cleaner call
# Firmware = db.table(FirmwareCore, pk="id", indexed=["name", "owner", "group"])


# @db.table(pk="id", indexed=["name", "owner", "group"])
# class Firmware(FirmwareCore):
#    data = constr(min_length=3, max_length=8_000_000)


@db.table(pk="id", indexed=["name", "owner", "group"])
class EnergyEnvironment(EnergyEnvironmentCore):
    pass


@db.table(pk="id", indexed=["name", "owner", "group"])
class VirtualHarvesterConfig(VirtualHarvesterConfigCore):
    pass


@db.table(pk="id", indexed=["name", "owner", "group"])
class VirtualSourceConfig(VirtualSourceConfigCore):
    pass


# ########################  TESTBED #################


# @db.table(pk="id", indexed=["name"])
# class Cape(CapeCore):
#    pass


@db.table(pk="id", indexed=["name"])
class GPIO(GPIOCore):
    pass


@db.table(pk="id", indexed=["name"])
class MCU(MCUCore):
    pass


@db.table(pk="id", indexed=["name"])
class Observer(ObserverCore):
    pass


# @db.table(pk="id", indexed=["name"])
# class Target(TargetCore):
#    pass


@db.table(pk="id", indexed=["name"])
class Testbed(TestbedCore):
    pass


# ########################  ReInit #################


async def models_init() -> None:
    async def _init() -> None:
        async with db._engine.begin() as conn:
            await db.init()
            await conn.run_sync(db._metadata.drop_all)
            await conn.run_sync(db._metadata.create_all)

    await _init()
    item_types = db._crud_generators.keys()
    # item_types = [type(data).__name__ for data in item_types]
    print(item_types)
    for _type in item_types:
        item_ids = tb_client.query_ids(model_type=type(_type).__name__)
        for _id in item_ids:
            item = tb_client.query_item(model_type=type(_type).__name__, uid=_id)
            await db[_type].insert(item)
