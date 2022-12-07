from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import constr, conint, confloat
from pydantic import BaseModel

from .d_VirtualSource_model import VirtualSource


class TargetPort(str, Enum):
    A = "A"
    B = "B"


class Compression(str, Enum):
    lzf = "lzf"
    gzip1 = "1"


class EmulatorIF(BaseModel):

#    name: constr(
#        strip_whitespace=True,
#        to_lower=True,
#        min_length=4,
#    )

    # General config
    input_path: Path
    output_path: Optional[Path]
    force_overwrite: bool = False
    compression: Optional[Compression] = None

    start_time: datetime  # = Field(default_factory=datetime.utcnow)
    duration: timedelta

    # emulation-specific
    use_cal_default: bool = False

    enable_io: bool = False
    io_target: TargetPort = "A"
    pwr_target: TargetPort = "A"
    aux_target_voltage: confloat(ge=0, le=5) = 0

    virtual_source: VirtualSource = {"name": "neutral"}


