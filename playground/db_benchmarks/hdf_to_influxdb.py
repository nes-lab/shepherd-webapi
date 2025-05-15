import time
from datetime import datetime
from multiprocessing import Process
from pathlib import Path

import h5py
import pandas as pd
from config_secrets import bucket
from config_secrets import org
from config_secrets import token
from influxdb_client import InfluxDBClient
from influxdb_client import WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.write_api import PointSettings

df_header = ["voltage", "current"]


def ds_to_phys(dataset: h5py.Dataset):
    gain = dataset.attrs["gain"]
    offset = dataset.attrs["offset"]
    return dataset[:] * gain + offset


def extract_hdf(hdf_file: Path) -> pd.DataFrame:
    with h5py.File(hdf_file, "r") as hf:
        data = []
        for var in df_header:
            sig_phys = ds_to_phys(hf["data"][var])
            data[var] = sig_phys

        time_index = hf["data"]["time"][:]
        data_len = min([len(time_index), len(data["voltage"]), len(data["current"])])
        time_index = time_index[:data_len]
        data["current"] = data["current"][:data_len]
        data["voltage"] = data["voltage"][:data_len]
        data_df = pd.DataFrame(data=data, columns=df_header, index=time_index)
        print("HDF extracted..")
    return data_df


def put_in_influx(data: pd.DataFrame, client_id: int):
    # take load off, this can also come from a toml-file
    point_setting = PointSettings()
    point_setting.add_default_tag("host", str(client_id))
    point_setting.add_default_tag("location", "roomX")
    # point_setting.add_default_tag("start", "210404200000")
    client = InfluxDBClient(
        url="http://10.0.0.39:8086",
        token=token,
        timeout=10000,
        enable_gzip=True,
    )
    write_client = client.write_api(
        point_settings=point_setting,
        write_options=SYNCHRONOUS,
    )  # Asynch makes no big difference
    batch_size = 50000  # link states optimum at 5k lines, https://docs.influxdata.com/influxdb/v2.0/write-data/best-practices/optimize-writes/
    sample_size = data.shape[0]
    for _iter in range(0, sample_size, batch_size):
        _i_end = max(_iter, min(_iter + batch_size, sample_size - 1))
        print(f"writing part: id{client_id} {_iter}:{_i_end}")
        write_client.write(
            bucket,
            org,
            record=data.iloc[_iter:_i_end, :],
            data_frame_measurement_name="my_meas5",
            write_precision=WritePrecision.NS,
        )
    write_client.close()
    client.close()


if __name__ == "__main__":
    proc_num = 16
    sample_size = 1000000
    data = extract_hdf(Path("rec.6.h5"))
    data = data.head(sample_size)
    print(f"Dataset data: {datetime.fromtimestamp(data.index[0] / 1e9)}")
    print(
        f"Writing Batch of: {data.shape} entries, {data.shape[0] / 1e5} sec\n {data.dtypes}",
    )
    print(data.iloc[0:5, :])

    time_start = time.time()

    procs = []
    for _iter in range(proc_num):
        process = Process(target=put_in_influx, args=(data, _iter))
        process.start()
        procs.append(process)
    print("Processes created")
    for process in procs:
        process.join()

    duration = round(time.time() - time_start, 2)
    insertsps = round(proc_num * sample_size / duration / 1000)
    print(
        f"Insertion took {duration} seconds, {insertsps} k/s for {proc_num} * {sample_size} items",
    )

# results:
# - inserting 200s data takes ~ 190s (1 node), with almost no load on VM or system
# - ram usage seems to be ok << 1 GB
# - query's with ns resolution can get very slow. ~3s for averaging windows
# - influx can almost naturally import hdf5, numpy-arrays, pandas Dataframes
# - asyncio does not work (threads)
# - multiprocessing-lib (one vServer, 1 host that inserts data) [8cores,HT]
#    - 1x 1M, 12.7 s, 79 k/s
#    - 4x 1M, 15.48, 258 k/s (~25 % cpu in vm)
#    - 8x 1M, 19.53, 410 k/s (~50 % cpu in vm)
#    - 16x 1M, 29.96, 534 k/s (~80 % cpu in vm, 1.8 GB ram usage of VM, 100% cpu of host)
#    - 32x 1M, 55.157, 580 k/s (~90 % cpu in vm, 1.8 GB ram usage of VM, 100% cpu of host)
#    - batch size (16x 1M):
#       - 05 k, 31.33 s, 511 k/s
#       - 10 k, 30.20 s, 530 k/s
#       - 20 k, 29.69 s, 539 k/s
#       - 40 k, 29.10 s, 550 k/s
#       - 50 k, 29.09 s, 550 k/s
