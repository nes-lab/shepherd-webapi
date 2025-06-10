"""This example shows how to download and delete experiments.

- files are stored in a subdirectory of the path that was provided.
- existing files are not overwritten, so only missing files are (re)downloaded.
"""

# start example
from pathlib import Path

from shepherd_client import Client

path_here = Path(__file__).parent

client = Client()

for xp_id in client.list_experiments(only_finished=True):
    client.download_experiment(xp_id, path_here)

# and later when you are sure your data is fine:
for xp_id in client.list_experiments(only_finished=True):
    client.delete_experiment(xp_id)
# end example

# ########### EXTRA ##################

# you can also directly delete your data after download

for xp_id in client.list_experiments(only_finished=True):
    client.download_experiment(xp_id, path_here, delete_on_server=True)
