import logging

log = logging.getLogger("asyncio")  # TODO: test instead of [shp_srv]


def set_verbosity(*, debug: bool = True) -> None:
    if debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)


def get_verbosity() -> bool:
    return log.level == logging.DEBUG


# short reminder for format-strings:
# %s    string
# %d    decimal
# %f    float
# %o    decimal as octal
# %x    decimal as hex
#
# %05d  pad right (aligned with 5chars)
# %-05d pad left (left aligned)
# %06.2f    6chars float, including dec point, with 2 chars after
# %.5s  truncate to 5 chars
#
# %% for a percent character
