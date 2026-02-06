"""Schedule lots of consecutive Experiments."""

# start example
import shepherd_core.data_models as sdm

from shepherd_client import Client

client = Client()

durations = [1, 2, 3, 15, 16, 25, 35, 55, 56, 57, 14, 8, 7, 6, 4]

for duration in durations:
    xp = sdm.Experiment(
        name=f"stresstest_{duration}min",
        duration=duration * 60,
        target_configs=[
            sdm.TargetConfig(
                target_IDs=range(1, 11),
                energy_env=sdm.EnergyEnvironment(name="synthetic_static_3000mV_50mA"),
                firmware1=sdm.Firmware(name="nrf52_rf_survey"),
                uart_logging=sdm.UartLogging(),  # default is 115200 baud
                gpio_tracing=sdm.GpioTracing(gpios=range(2, 18)),
            ),
        ],
    )

    xp_id = client.create_experiment(xp)
    print(xp_id)
    client.schedule_experiment(xp_id)
# end example
