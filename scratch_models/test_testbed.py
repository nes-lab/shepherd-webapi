from pathlib import Path

import yaml

print("INIT from preRead file")
emu_path = Path("example_config_testbed.yml").absolute()
with open(emu_path) as file_data:
    tb_cfg = yaml.safe_load(file_data)  # ["parameters"]
if isinstance(tb_cfg, str):
    # vs_mdl = EmulatorIF(name=emu_cfg)
    pass
elif isinstance(tb_cfg, dict):
    # vs_mdl = EmulatorIF.parse_obj(emu_cfg)
    pass
else:
    raise TypeError
