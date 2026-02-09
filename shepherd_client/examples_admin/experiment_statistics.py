from pathlib import Path

import isodate
import pandas as pd
from shepherd_core import log
from tqdm import tqdm

from shepherd_client import AdminClient

file_result = Path(__file__).with_suffix(".csv")

client = AdminClient()

# load locally if available
data = (
    pd.read_csv(file_result)
    if file_result.exists()
    else pd.DataFrame(columns=["_id", "state", "duration", "created_at", "deleted_at"])
).set_index("_id")

# update - only non-deleted entries
xp_ids = [
    xp_id
    for xp_id in client.list_all_experiments()
    if xp_id not in data.index or pd.isna(data.loc[xp_id, "deleted_at"])
]
data_new = [
    client.get_experiment_statistics(xp_id) for xp_id in tqdm(xp_ids, "fetching experiments")
]
data = pd.concat([data.reset_index(), pd.DataFrame(data=data_new)])
data = data.drop_duplicates("_id", keep="last").sort_values("created_at").set_index("_id")

# store locally
data.reset_index().to_csv(file_result)

# analyze
log.info("Found:")
data["duration"] = data["duration"].apply(isodate.parse_duration)
log.info(
    "- %i total experiments, %.1f MiB, runtime is %s",
    len(data),
    data["result_size"].sum() / 1024 / 1024,
    data["duration"].sum(),
)

ddel = data[data["deleted_at"].isna()]
log.info(
    "- %i XPs still stored in DB, %.1f MiB, runtime is %s",
    len(ddel),
    ddel["result_size"].sum() / 1024 / 1024,
    ddel["duration"].sum(),
)

derr = data[data["had_errors"]]
log.info(
    "- %i XPs had errors (%.2f %%, %.2f %% by runtime)",
    len(derr),
    100 * derr["duration"].sum() / data["duration"].sum(),
    100 * len(derr) / len(data),
)

for state in ["created", "scheduled", "running", "finished"]:
    data_state = data[data["state"] == state]
    if len(data_state) > 0:
        log.info(
            "- %i %s-state XPs, runtime is %s",
            len(data_state),
            state,
            data_state["duration"].sum(),
        )

# TODO: add
#  - monthly stats?
