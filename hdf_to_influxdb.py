from datetime import datetime
import time
import h5py
import pandas as pd
from pathlib import Path
from influxdb_client.client.write_api import SYNCHRONOUS, PointSettings
from influxdb_client import InfluxDBClient, WritePrecision
from config_secret import bucket, org, token
import asyncio

df_header = ["voltage", "current"]


def ds_to_phys(dataset: h5py.Dataset):
    gain = dataset.attrs["gain"]
    offset = dataset.attrs["offset"]
    return dataset[:] * gain + offset


def extract_hdf(hdf_file: Path) -> pd.DataFrame:
    with h5py.File(hdf_file, "r") as hf:
        data = dict()
        for var in df_header:
            sig_phys = ds_to_phys(hf["data"][var])
            data[var] = sig_phys

        time_index = hf["data"]["time"][:]
        data_len = min(
            [len(time_index), len(data["voltage"]), len(data["current"])]
        )
        time_index = time_index[:data_len]
        data["current"] = data["current"][:data_len]
        data["voltage"] = data["voltage"][:data_len]
        df = pd.DataFrame(data=data, columns=df_header, index=time_index)
        print("HDF extracted..")
    return df


async def put_in_influx(data: pd.DataFrame, client_id: int):
    # take load off, this can also come from a toml-file
    point_setting = PointSettings()
    point_setting.add_default_tag("host", str(client_id))
    point_setting.add_default_tag("location", "roomX")
    #point_setting.add_default_tag("start", "210404200000")
    client = InfluxDBClient(url="http://10.0.0.39:8086", token=token, timeout=10000, enable_gzip=False)
    write_client = client.write_api(point_settings=point_setting, write_options=SYNCHRONOUS)  # Asynch makes no big difference
    batch_size = 20000  # link states optimum at 5k lines, https://docs.influxdata.com/influxdb/v2.0/write-data/best-practices/optimize-writes/
    sample_size = 1000000  #data.shape[0]
    for iter in range(0, sample_size, batch_size):
        iter_stop = max(iter, min(iter + batch_size, sample_size - 1))
        print(f"writing part: id{client_id} {iter}:{iter_stop}")
        write_client.write(bucket, org, record=data.iloc[iter:iter_stop, :], data_frame_measurement_name='my_meas5', write_precision=WritePrecision.NS)
    write_client.close()
    client.close()


async def scheduler(data: pd.DataFrame):
    tasks = list()
    for iter in range(4):
        tasks.append(asyncio.create_task(put_in_influx(data, iter)))
        #tasks.append(asyncio.to_thread(put_in_influx, data, iter))
    print("Tasks created")
    for task in tasks:
        await task
        #await asyncio.gather(task)

if __name__ == "__main__":
    data = extract_hdf(Path("./rec.6.h5"))
    print(f"Dataset data: {datetime.fromtimestamp(data.index[0]/1e9)}")
    print(f"Writing Batch of: {data.shape} entries, {data.shape[0]/1e5} sec\n {data.dtypes}")
    print(data.iloc[0:5, :])
    time_start = time.time()
    asyncio.run(scheduler(data))
    print(f"Insertion took {round(time.time() - time_start, 2)} seconds")

# results:
# - inserting 200s data takes ~ 190s (1 node), with almost no load on VM or system
# - ram usage seems to be ok << 1 GB
# - query's with ns resolution can get very slow. ~3s for averaging windows
# - influx can almost naturally import hdf5, numpy-arrays, pandas Dataframes

