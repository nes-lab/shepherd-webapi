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
#vs_dict["io_port"] = str(vs_dict["io_port"])
#vs_dict["pwr_port"] = str(vs_dict["pwr_port"])
vs_dict["virtual_source"]["harvester"]["datatype"] = \
    str(vs_dict["virtual_source"]["harvester"]["datatype"])


with open("example_config_emulator_out.yml", "w") as file_yml:
    yaml.safe_dump(vs_dict, file_yml, default_flow_style=False, sort_keys=False,)
