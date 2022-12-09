import base64
from pathlib import Path

import yaml
from models.d_Emulator_interface import EmulatorIF

print("INIT from preRead file")
emu_path = Path("example_config_emulator.yml").absolute()
with open(emu_path) as file_data:
    emu_cfg = yaml.safe_load(file_data)["parameters"]
if isinstance(emu_cfg, str):
    vs_mdl = EmulatorIF(name=emu_cfg)
elif isinstance(emu_cfg, dict):
    vs_mdl = EmulatorIF.parse_obj(emu_cfg)
else:
    raise TypeError


vs_dict = vs_mdl.dict(exclude_defaults=True, exclude_unset=True)
print(vs_dict)
# Dirty Test ...
vs_dict["input_path"] = str(vs_dict["input_path"])
vs_dict["output_path"] = str(vs_dict["output_path"])
vs_dict["duration"] = str(vs_dict["duration"])
# vs_dict["io_port"] = str(vs_dict["io_port"])
# vs_dict["pwr_port"] = str(vs_dict["pwr_port"])
vs_dict["virtual_source"]["harvester"]["datatype"] = str(
    vs_dict["virtual_source"]["harvester"]["datatype"],
)
vs_dict["image_data"] = base64.standard_b64encode(
    b"TestString: This module provides functions for encoding binary data to printable ASCII characters and decoding such encodings back to binary data. It provides encoding and decoding functions for the encodings specified in RFC 4648, which defines the Base16, Base32, and Base64 algorithms, and for the de-facto standard Ascii85 and Base85 encodings.",
)

print(base64.standard_b64decode(vs_dict["image_data"]))


with open("example_config_emulator_out.yml", "w") as file_yml:
    yaml.safe_dump(vs_dict, file_yml, default_flow_style=False, sort_keys=False)

vs_mdl.get_parameters()
