import param


class VirtualSourceBase(param.Parameterized):
    efficiency_opt = 12 * [param.Magnitude(1.00)]

    name = param.String("neutral")
    # converter_base = param.String(None, allow_None=True)
    enable_boost = param.Boolean(False, allow_None=True)
    enable_buck = param.Boolean(False, allow_None=True)
    log_intermediate_voltage = param.Boolean(False, allow_None=True)

    interval_startup_delay_drain_ms = param.Number(
        0,
        bounds=(0, 10_000),
        allow_None=True,
    )

    harvester = param.String("mppt_opt", allow_None=True)

    V_input_max_mV = param.Number(10000, bounds=(0, 10e3), allow_None=True)
    I_input_max_mA = param.Number(4200, bounds=(0, 4.29e3), allow_None=True)
    V_input_drop_mV = param.Number(0.0, bounds=(0, 4.29e6), allow_None=True)

    C_intermediate_uF = param.Number(0.0, bounds=(0, 100e3), allow_None=True)
    V_intermediate_init_mV = param.Number(3000, bounds=(0, 10e3), allow_None=True)
    I_intermediate_leak_nA = param.Number(0.0, bounds=(0, 4.29e9), allow_None=True)

    LUT_output_efficiency = param.List(
        efficiency_opt,
        item_type=param.Magnitude,
        bounds=(12, 12),
        allow_None=True,
    )

    @param.depends(on_init=True)
    def _check(self):
        pass


class VirtualSource(VirtualSourceBase):

    name = param.String()
    converter_base = param.String("neutral")


# TODO: what is missing
#   - chain of inheritance
#   -
