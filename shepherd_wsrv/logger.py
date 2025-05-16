import logging
import logging.handlers

import chromalog

chromalog.basicConfig(format="%(message)s")
log = logging.getLogger("[shp_wsrv]")
log.addHandler(logging.NullHandler())
log.setLevel(logging.INFO)


def set_verbosity(*, debug: bool = False) -> None:
    if debug:
        log.setLevel(logging.DEBUG)
        logging.basicConfig(format="%(name)s %(levelname)s: %(message)s")
    else:
        log.setLevel(logging.INFO)
        logging.basicConfig(format="%(message)s", force=True)
        # only needed in debug mode:
        logging._srcfile = None  # noqa: SLF001
        logging.logThreads = False
        logging.logProcesses = False


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
