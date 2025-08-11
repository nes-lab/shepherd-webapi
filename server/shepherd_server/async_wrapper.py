"""A wrapper to remove boilerplate-code.

@async_wrap(timeout=4)
def give_me_5(name: str) -> str:
    time.sleep(5)
    return f"hello {name}"

async def runner():
    ret, err_msg = await give_me_5("peter")
    print(ret)

asyncio.run(runner())

"""

import asyncio
from collections.abc import Awaitable
from collections.abc import Callable
from functools import wraps
from typing import Any
from typing import TypeVar

from server.shepherd_server.logger import log

F = TypeVar("F", bound=Callable[..., Any])


def async_wrap(timeout: float | None = None) -> Callable[[F], Callable[..., Awaitable[Any]]]:
    """
    Decorator that wraps a blocking function to make it async with optional timeout.
    It runs it in a separate thread with asyncio.to_thread(),
    and adds a timeout with asyncio.wait_for().
    This wrapper also catches exceptions and returns a custom error message as 2nd return arg.

    Args:
        timeout: Maximum time in seconds to wait (None for no timeout).

    Returns:
        The future result and an optional error message.

    Raises:
        asyncio.TimeoutError: If the function takes longer than timeout seconds
    """

    def decorator(func: F) -> Callable[..., Awaitable[Any]]:
        @wraps(func)  # Preserves name, docstring, etc.
        async def wrapper(*args, **kwargs) -> Any:  # noqa: ANN002, ANN003
            # Run the blocking function in a separate thread
            thread_task = asyncio.to_thread(func, *args, **kwargs)
            result = None
            fn_name = getattr(func, "__name__", repr(callable))
            try:
                result = (
                    await thread_task
                    if timeout is None
                    else await asyncio.wait_for(thread_task, timeout=timeout)
                )
            except asyncio.TimeoutError:
                error_msg = f"Timeout ({timeout} s) running {fn_name}"
            except RuntimeError as xpt:
                error_msg = f"Caught runtime error ({xpt}) running {fn_name}"
            except Exception as xpt:  # noqa: BLE001
                error_msg = f"Caught general exception ({xpt}) running {fn_name}"
            else:
                error_msg = None
            if error_msg is not None:
                log.warning(error_msg)
            return result, error_msg

        return wrapper

    return decorator
