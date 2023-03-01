from pydantic import BaseModel
from pydantic import conint


class PowerLogging(BaseModel):
    # initial recording
    log_voltage: bool = True
    log_current: bool = True
    # compression: Optional[Compression] = None  # -> to Emu
    log_intermediate_voltage: bool = False  # TODO: duplicate in PowerSampling()

    # post-processing, TODO: not supported ATM
    calculate_power: bool = False
    samplerate: conint(ge=100, le=100_000) = 100_000
    discard_current: bool = False
    discard_voltage: bool = False

    class Config:
        # title = "Virtual Source MinDef"
        allow_mutation = False  # const after creation?
        extra = "forbid"  # no unnamed attributes allowed
        validate_all = True  # also check defaults
        min_anystr_length = 4
        anystr_lower = True
        anystr_strip_whitespace = True  # strip leading & trailing whitespaces


class GpioLogging(BaseModel):
    # initial recording
    log_gpio: bool = False  # TODO: activate
    mask: conint(ge=0, le=2**10) = 2**10  # all

    # post-processing, TODO: not supported ATM
    decode_uart: bool = False
    baudrate_uart: conint(ge=2_400, le=921_600) = 115_200
    # TODO: more uart-config -> dedicated interface?

    class Config:
        # title = "Virtual Source MinDef"
        allow_mutation = False  # const after creation?
        extra = "forbid"  # no unnamed attributes allowed
        validate_all = True  # also check defaults
        min_anystr_length = 4
        anystr_lower = True
        anystr_strip_whitespace = True  # strip leading & trailing whitespaces


class SystemLogging(BaseModel):
    log_dmesg: bool = False  # TODO: activate
    log_ptp: bool = False  # TODO: activate

    class Config:
        # title = "Virtual Source MinDef"
        allow_mutation = False  # const after creation?
        extra = "forbid"  # no unnamed attributes allowed
        validate_all = True  # also check defaults
        min_anystr_length = 4
        anystr_lower = True
        anystr_strip_whitespace = True  # strip leading & trailing whitespaces
