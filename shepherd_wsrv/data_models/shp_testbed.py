from typing import Optional

from pydantic import BaseModel

from beanie import Document, Indexed, init_beanie
from shepherd_core.data_models.testbed import GPIO as GPIOCore
from shepherd_core.data_models.testbed import MCU as MCUCore
from shepherd_core.data_models.testbed import Observer as ObserverCore
from shepherd_core.data_models.testbed import Testbed as TestbedCore
from shepherd_core.testbed_client import tb_client
