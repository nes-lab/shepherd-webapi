import time
from datetime import datetime

import pandas as pd
from config_secrets import bucket
from config_secrets import client
from config_secrets import org

# from influxdb_client.client.bucket_api import
from influxdb_client import Point
from influxdb_client import WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.write_api import PointSettings

# lib-readme    https://influxdb-client.readthedocs.io/en/latest/usage.html
# line protocol https://docs.influxdata.com/influxdb/v1.8/write_protocols/line_protocol_tutorial/
# - measurement -> user_timestamp, system, log
# - tag_set
#   - host      -> BB-node
#   - what else? config, room, gps-coord?, position in grid (x,y) in cm
# - field_set
#   - voltage
#   - current
#   - charge
# - timestamp
# Best Practice https://docs.influxdata.com/influxdb/v2.0/write-data/best-practices/schema-design/

# TODO: try asynchronous, but don't forget to flush


# Creating a bucket


# Writing

# take load off, this can also come from a toml-file
point_setting = PointSettings()
point_setting.add_default_tag("host", "BB_0")
point_setting.add_default_tag("location", "roomX")
point_setting.add_default_tag("start", "210404200000")

write_client = client.write_api(point_settings=point_setting, write_options=SYNCHRONOUS)

# each point separate
for _iter in range(100):
    ts = round(time.time() * 1e9)  # returns nanosecond timestamp
    data = f"my_meas1 voltage={23 + _iter / 100} {ts}"  # line protocol
    write_client.write(bucket, org, data, write_precision=WritePrecision.NS)

print(f"separate Point VarA: {data}")

# alternative: use api, but previous raw should be faster
data = Point("my_meas2").tag("location", "lab").field("voltage", 40.0).time(datetime.now())
write_client.write(bucket, org, data, write_precision=WritePrecision.NS)
print(f"separate Point VarB: {data}")

# batch-write a window of data -> perfect for our use-case
# - high throughput
sequence = [
    "my_meas3,host=BB-3 voltage=23.43234543",
    "my_meas3,host=BB-3 voltage=15.856523",
]
write_client.write(bucket, org, sequence)
print(f"batch write    VarA: {sequence[0]}")

# alternative: direct dataframe
_now = round(time.time() * 1e9)
_data_frame = pd.DataFrame(
    data=[["roomY", 1.0], ["roomY", 2.0]],
    index=[_now, _now + 5000],
    columns=["location", "voltage"],
)

write_client.write(
    bucket,
    org,
    record=_data_frame,
    data_frame_measurement_name="my_meas4",
    data_frame_tag_columns=["location"],
    write_precision=WritePrecision.NS,
)
print(f"batch write    VarB: {_data_frame}")

client.close()
