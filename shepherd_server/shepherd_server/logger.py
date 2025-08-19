import atexit
import logging
import multiprocessing
from logging import handlers

log = logging.getLogger("[shp_srv]")

for hdlr in log.handlers:
    log.removeHandler(hdlr)
log.propagate = False
queue = multiprocessing.Queue(-1)
queue_handler = handlers.QueueHandler(queue)
queue_handler.setLevel(logging.INFO)
log.addHandler(queue_handler)

listener = handlers.QueueListener(queue, logging.StreamHandler())
listener.start()


def set_verbosity(*, debug: bool = True) -> None:
    if debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)


def get_verbosity() -> bool:
    return log.level == logging.DEBUG


def clear_message_queue() -> None:
    """If no one reads the queue, the thread will not finish, so add option to empty it"""
    log.removeHandler(queue_handler)
    listener.stop()
    queue.cancel_join_thread()
    queue.close()


# last action on exit is to clear queue to prevent lockup
atexit.register(clear_message_queue)

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
