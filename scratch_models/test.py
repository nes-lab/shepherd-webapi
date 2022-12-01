target_pin_nums = [  # pin-order from target-connector
    {"name": "gpio0", "pin": 26, "dir": 78},
    {"name": "gpio1", "pin": 27, "dir": 78},
    {"name": "gpio2", "pin": 46, "dir": 78},
    {"name": "gpio3", "pin": 47, "dir": 78},
    {"name": "gpio4", "pin": 61, "dir": "I"},
    {"name": "gpio5", "pin": 80, "dir": "I"},
    {"name": "gpio6", "pin": 81, "dir": "I"},
    {"name": "uart_rx", "pin": 14, "dir": "I"},
    {"name": "uart_tx", "pin": 15, "dir": 79},
    {"name": "swd1_clk", "pin": 5, "dir": "O"},
    {"name": "swd1_io", "pin": 4, "dir": 10},
    {"name": "swd2_clk", "pin": 8, "dir": "O"},
    {"name": "swd2_io", "pin": 9, "dir": 11},
]

dir_pins = {pin["dir"] for pin in target_pin_nums if isinstance(pin["dir"], int)}
print(dir_pins)
dirs = {}
for pin in dir_pins:
    dirs[pin] = pin

print(dirs)
