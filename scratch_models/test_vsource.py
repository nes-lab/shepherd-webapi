from pathlib import Path

import yaml
from models.d_VirtualSource_model import VirtualSource

# TODO open Problem:
# - provide custom fixtures
# - load module by name

print("INIT direct-VSource")
pvs_d = VirtualSource(name="direct", inherit_from="neutral")

print("INIT diode&Cap-VSource")
pvs_dicap = VirtualSource(
    name="diode+capacitor",
    V_input_drop_mV=300,
    C_intermediate_uF=10,
)

print(pvs_dicap.harvester)
print(pvs_dicap.dict())

print("INIT special-VSource")
pvs_spec = VirtualSource(
    name="special",
    inherit_from="BQ25570si",
    V_output_mV=3300,
)
print(pvs_spec.dict())

print("INIT from preRead file")
vs_path = Path("example_config_virtsource.yml").absolute()
with open(vs_path) as file_data:
    vs_cfg = yaml.safe_load(file_data)["VirtualSource"]
if isinstance(vs_cfg, str):
    vs_mdl = VirtualSource(name=vs_cfg)
elif isinstance(vs_cfg, dict):
    vs_mdl = VirtualSource.parse_obj(vs_cfg)
else:
    raise TypeError

# print("INIT from file") # -> json and pickle only
# vs_mf = VirtualSource.parse_file(vs_path)
