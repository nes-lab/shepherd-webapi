from pathlib import Path

from pandas import DataFrame

from shepherd_client import AdminClient

client = AdminClient()

xp_ids = client.list_all_experiments()

xp_stats = []
for xp_id in xp_ids:
    xp_stats.append = client.get_experiment_statistics(xp_id)

data = DataFrame.from_dict(xp_stats)
data.to_csv(Path(__file__).with_suffix(".csv"))
