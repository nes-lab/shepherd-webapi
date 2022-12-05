from pathlib import Path

import yaml
from .d_VirtualHarvester_model import VirtualHarvester
from pydantic import BaseModel
from pydantic import confloat
from pydantic import conint
from pydantic import conlist
from pydantic import constr
from pydantic import root_validator


def load_vsources() -> dict:
    def_file = "d_VirtualSource_fixtures.yml"
    def_path = Path(__file__).parent.resolve() / def_file
    with open(def_path) as def_data:
        configs = yaml.safe_load(def_data)["virtsources"]
        configs = {k.lower(): v for k, v in configs.items()}
    return configs


configs_predef = load_vsources()


def acquire_def(name: str):
    name = name.lower()
    if name in configs_predef:
        config_base = configs_predef[name]
        return config_base
    else:
        ValueError(f"ConverterBase {name} not known!")


# TODO: use title, alias,


class VirtualSourceMin(BaseModel):

    # General Config
    name: constr(
        strip_whitespace=True,
        to_lower=True,
        min_length=4,
    ) = "neutral"
    converter_base: constr(
        strip_whitespace=True,
        to_lower=True,
        min_length=4,
    ) = "neutral"

    enable_boost: bool = False
    enable_buck: bool = False
    log_intermediate_voltage: bool = False

    interval_startup_delay_drain_ms: confloat(ge=0, le=10e3) = 0

    harvester: VirtualHarvester = VirtualHarvester(name="mppt_opt")

    V_input_max_mV: confloat(ge=0, le=10e3) = 10_000
    I_input_max_mA: confloat(ge=0, le=4.29e3) = 4_200
    V_input_drop_mV: confloat(ge=0, le=4.29e6) = 0
    R_input_mOhm: confloat(ge=0, le=4.29e6) = 0

    C_intermediate_uF: confloat(ge=0, le=100_000) = 0
    V_intermediate_init_mV: confloat(ge=0, le=10_000) = 3_000
    I_intermediate_leak_nA: confloat(ge=0, le=4.29e9) = 0

    V_intermediate_enable_threshold_mV: confloat(ge=0, le=10_000) = 1
    V_intermediate_disable_threshold_mV: confloat(ge=0, le=10_000) = 0
    interval_check_thresholds_ms: confloat(ge=0, le=4.29e3) = 0

    V_pwr_good_enable_threshold_mV: confloat(ge=0, le=10_000) = 2_800
    V_pwr_good_disable_threshold_mV: confloat(ge=0, le=10_000) = 2200
    immediate_pwr_good_signal: bool = True

    C_output_uF: confloat(ge=0, le=4.29e6) = 1.0

    # Extra
    V_output_log_gpio_threshold_mV: confloat(ge=0, le=4.29e6) = 1_400

    # Boost Converter
    V_input_boost_threshold_mV: confloat(ge=0, le=10_000) = 0
    V_intermediate_max_mV: confloat(ge=0, le=10_000) = 10_000

    LUT_input_efficiency: conlist(
        item_type=conlist(confloat(ge=0.0, le=1.0), min_items=12, max_items=12),
        min_items=12,
        max_items=12,
    ) = 12 * [12 * [1.00]]
    LUT_input_V_min_log2_uV: conint(ge=0, le=20) = 0
    LUT_input_I_min_log2_nA: conint(ge=0, le=20) = 0

    # Buck Converter
    V_output_mV: confloat(ge=0, le=5_000) = 2_400
    V_buck_drop_mV: confloat(ge=0, le=5_000) = 0

    LUT_output_efficiency: conlist(
        item_type=confloat(ge=0.0, le=1.0),
        min_items=12,
        max_items=12,
    ) = 12 * [1.00]
    LUT_output_I_min_log2_nA: conint(ge=0, le=20) = 0

    @root_validator(pre=True)
    def recursive_fill(cls, values):

        if "converter_base" in values:
            config_name = values.get("converter_base")
            config_base = acquire_def(config_name)
            print(f"Will init VSrc from {config_name}")
            config_base["name"] = config_name
            base_dict = VirtualSourceMin.recursive_fill(values=config_base)
            for key, value in values.items():
                base_dict[key] = value
            values = base_dict
        elif "name" in values and values.get("name").lower() in configs_predef:
            config_name = values.get("name").lower()
            if config_name == "neutral":
                values = acquire_def(config_name)
                values["name"] = config_name
            else:
                config_base = acquire_def(config_name)
                print(f"Will init VSrc as {config_name}")
                config_base["name"] = config_name
                values = VirtualSourceMin.recursive_fill(values=config_base)
        return values

    @root_validator(pre=False)
    def post_adjust(cls, values):
        # TODO
        return values

    def get_parameters(self):
        pass
