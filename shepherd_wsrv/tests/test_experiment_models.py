import datetime
from shepherd_wsrv.api_experiment.models import WebExperiment
from shepherd_core.data_models.experiment import Experiment

async def test_get_next_scheduling(
    sample_experiment: Experiment,
    database_for_tests: None,
):
    assert await WebExperiment.get_next_scheduling() is None

    one = WebExperiment(experiment=sample_experiment)
    await one.save()

    assert await WebExperiment.get_next_scheduling() is None

    one.scheduled_at = datetime.date(2000, 1, 1)
    await one.save()

    assert await WebExperiment.get_next_scheduling() == one

    two = WebExperiment(experiment=sample_experiment)
    await two.save()

    assert await WebExperiment.get_next_scheduling() == one
    two.scheduled_at = datetime.date(2001, 1, 1)
    await two.save()

    assert await WebExperiment.get_next_scheduling() == one

    two.scheduled_at = datetime.date(1999, 1, 1)
    await two.save()

    assert await WebExperiment.get_next_scheduling() == two
