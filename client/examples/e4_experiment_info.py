"""Example for getting info about experiments stored on the testbed.

There are three options to get info
- .list_experiments() will provide a dictionary with ID and state of all experiments
- .get_experiment() will get the experiment-configuration itself back
- .get_experiment_state() allows to get the state of a specific experiment
"""

# start example
from shepherd_client import Client

client = Client()

experiments = client.list_experiments()

for key, value in experiments.items():
    print(f"{key}:\t{value}")

if len(experiments) > 0:
    xp_id = next(iter(experiments))
    xp = client.get_experiment(xp_id)
    print("UUID: ", xp_id)
    print("name: ", xp.name)
    print("state: ", client.get_experiment_state(xp_id))
# end example
