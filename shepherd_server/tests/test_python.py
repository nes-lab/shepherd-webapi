from datetime import timedelta

from shepherd_core import local_now


def test_datatime_comparison() -> None:
    exe_delay = timedelta(seconds=50)  # to better synchronize start
    exe_timestamp = local_now() + exe_delay
    assert exe_timestamp > local_now()


def test_datatime_tz_droppingcomparison() -> None:
    exe_delay = timedelta(seconds=50)  # to better synchronize start
    now = local_now()
    exe_timestamp = (now + exe_delay).replace(tzinfo=None)
    assert exe_timestamp == now.replace(tzinfo=None) + exe_delay
