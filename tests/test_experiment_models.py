import datetime

from shepherd_core.data_models.experiment import Experiment

from shepherd_wsrv.api_experiment.models import WebExperiment


async def test_get_next_scheduling(
    sample_experiment: Experiment,
    *,
    database_for_tests: bool,
) -> None:
    assert database_for_tests
    await WebExperiment.delete_all()
    assert await WebExperiment.get_next_scheduling() is None

    one = WebExperiment(experiment=sample_experiment)
    await one.save()

    assert await WebExperiment.get_next_scheduling() is None

    one.requested_execution_at = datetime.date(2000, 1, 1)
    await one.save()

    assert await WebExperiment.get_next_scheduling() == one

    two = WebExperiment(experiment=sample_experiment)
    await two.save()

    assert await WebExperiment.get_next_scheduling() == one
    two.requested_execution_at = datetime.date(2001, 1, 1)
    await two.save()

    assert await WebExperiment.get_next_scheduling() == one

    two.requested_execution_at = datetime.date(1999, 1, 1)
    await two.save()

    two.started_at = datetime.date(1999, 1, 1)
    await two.save()

    assert await WebExperiment.get_next_scheduling() == one
