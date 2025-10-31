import datetime

from shepherd_core import local_tz
from shepherd_core.data_models.experiment import Experiment
from shepherd_server.api_experiment.models import WebExperiment
from shepherd_server.api_user.models import User


async def test_get_next_scheduling(
    sample_experiment: Experiment,
    *,
    database_for_tests: bool,
) -> None:
    assert database_for_tests
    await WebExperiment.delete_all()
    assert await WebExperiment.get_next_scheduling() is None
    user = await User.by_email("user@test.com")
    one = WebExperiment(experiment=sample_experiment, owner=user)
    await one.save()

    assert await WebExperiment.get_next_scheduling() is None

    tzone = local_tz()
    one.requested_execution_at = datetime.datetime(2000, 1, 1, tzinfo=tzone)
    await one.save_changes()

    _next = await WebExperiment.get_next_scheduling()
    assert _next.id == one.id

    two = WebExperiment(experiment=sample_experiment, owner=user)
    await two.save()

    _next = await WebExperiment.get_next_scheduling()
    assert _next.id == one.id
    two.requested_execution_at = datetime.datetime(2001, 1, 1, tzinfo=tzone)
    await two.save_changes()

    _next = await WebExperiment.get_next_scheduling()
    assert _next.id == one.id

    two.requested_execution_at = datetime.datetime(1999, 1, 1, tzinfo=tzone)
    await two.save_changes()

    _next = await WebExperiment.get_next_scheduling()
    assert _next.id == two.id

    two.started_at = datetime.datetime(1999, 1, 1, tzinfo=tzone)
    await two.save_changes()

    _next = await WebExperiment.get_next_scheduling()
    assert _next.id == one.id
