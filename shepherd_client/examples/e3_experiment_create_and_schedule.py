"""Uploading and Scheduling an Experiment.

- upon creation, the experiment is checked for its validity
- if the testbed accepts the experiment, it will return an ID
- that ID can now be used to schedule the experiment or get infos
    - scheduling will fail if your quota is exceeded
- the state of the experiment progresses from:
        created -> scheduled -> running -> finished
"""

# start example
import shepherd_core.data_models as sdm

from shepherd_client import Client

client = Client()

xp = sdm.Experiment(
    name="my_own_survey",
    duration=3 * 60,
    target_configs=[
        sdm.TargetConfig(
            target_IDs=range(1, 11),
            energy_env=sdm.EnergyEnvironment(name="eenv_static_3000mV_50mA_3600s"),
            firmware1=sdm.Firmware(name="nrf52_rf_survey"),
            uart_logging=sdm.UartLogging(),  # default is 115200 baud
        ),
    ],
)

xp_id = client.create_experiment(xp)
client.schedule_experiment(xp_id)
# end example

# ########### EXTRA ##################

# Experiments can be scripted for parameter sweeps, etc.
# To simplify code it is possible to mass-schedule, as only "created" experiments are really queued

for xp_id in client.list_experiments():
    client.schedule_experiment(xp_id)
