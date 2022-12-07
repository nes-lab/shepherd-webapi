from enum import Enum
from typing import Optional

from pydantic import BaseModel, conint



class PowerSampling(BaseModel):

    # initial recording
    rec_voltage: bool = True
    rec_current: bool = True
    # compression: Optional[Compression] = None  # -> to Emu
    log_intermediate_voltage: bool = False  # TODO: duplicate in PowerSampling()

    # post-processing, TODO: not supported ATM
    calculate_power: bool = False
    samplerate: conint(ge=100, le=100_000) = 100_000
    discard_current: bool = False
    discard_voltage: bool = False


class GpioSampling(BaseModel):

    # initial recording
    mask: conint(ge=0, le=2**10) = 2**10  # all

    # post-processing, TODO: not supported ATM
    decode_uart: bool = False
    uart_baudrate: conint(ge=2_400, le=921_600) = 115_200
    # TODO: more uart-config -> dedicated interface?


class SysLogging(BaseModel):

    log_dmesg: bool = False
    log_ptp: bool = False
