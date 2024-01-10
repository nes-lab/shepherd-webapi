from typing import Optional

from pydantic import BaseModel

from beanie import Document, Indexed, init_beanie
from shepherd_core.data_models.content import EnergyEnvironment as EnergyEnvironmentCore
from shepherd_core.data_models.content import VirtualHarvesterConfig as VirtualHarvesterConfigCore
from shepherd_core.data_models.content import VirtualSourceConfig as VirtualSourceConfigCore
