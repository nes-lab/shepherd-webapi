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
