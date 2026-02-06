from pathlib import Path

from pandas import DataFrame
from shepherd_core import log

from shepherd_client import AdminClient

client = AdminClient()

xp_ids = client.list_all_experiments()
log.info(f"Fill fetch data from {len(xp_ids)} experiments")

xp_stats = [client.get_experiment_statistics(xp_id) for xp_id in xp_ids]

data = DataFrame(data=xp_stats)
data.to_csv(Path(__file__).with_suffix(".csv"))
