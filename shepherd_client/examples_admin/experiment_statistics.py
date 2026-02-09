from pathlib import Path

import isodate
import pandas as pd
from shepherd_core import log

from shepherd_client import AdminClient

client = AdminClient()

file_result = Path(__file__).with_suffix(".csv")

if not file_result.exists():
    xp_ids = client.list_all_experiments()
    log.info(f"Fill fetch data from {len(xp_ids)} experiments")

    xp_stats = [client.get_experiment_statistics(xp_id) for xp_id in xp_ids]

    data = pd.DataFrame(data=xp_stats)
    data.to_csv(file_result)
else:
    data = pd.read_csv(file_result)

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
