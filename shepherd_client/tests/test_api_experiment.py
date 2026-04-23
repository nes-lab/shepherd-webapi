from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pytest
from shepherd_client.client_user import UserClient
from shepherd_core import local_now
from shepherd_core.data_models import Experiment
from shepherd_core.data_models import TargetConfig
from shepherd_server.config import server_config

from shepherd_client import AdminClient

# ###############################################################################
# LIST
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_list_experiments(user1_client: UserClient) -> None:
    uids = user1_client.list_experiments()
    assert len(uids) > 0


@pytest.mark.usefixtures("_server_api_up")
def test_list_finished_experiments(user1_client: UserClient) -> None:
    uids_all = user1_client.list_experiments(only_finished=False)
    uids_fin = user1_client.list_experiments(only_finished=True)
    assert len(uids_fin) > 0
    assert len(uids_all) > len(uids_fin)
    assert set(uids_all) & set(uids_fin) == set(uids_fin)  # all finished in ALL


@pytest.mark.usefixtures("_server_api_up")
def test_list_experiments_admin_all(admin_client: AdminClient) -> None:
    uids1 = admin_client.list_experiments()
    uids2 = admin_client.list_all_experiments()
    assert len(uids2) >= len(uids1)
    assert len(uids2) > 0


# ###############################################################################
# CREATE
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_create_experiment(user1_client: UserClient, sample_experiment: Experiment) -> None:
    assert user1_client.create_experiment(sample_experiment) is not None


@pytest.mark.usefixtures("_server_api_up")
def test_create_experiment_is_authenticated(
    unconfirmed_client: UserClient, sample_experiment: Experiment
) -> None:
    assert unconfirmed_client.create_experiment(sample_experiment) is None


@pytest.mark.usefixtures("_server_api_up")
def test_create_experiment_as_admin_succeeds(
    admin_client: UserClient, sample_experiment: Experiment
) -> None:
    assert admin_client.create_experiment(sample_experiment) is not None


@pytest.mark.usefixtures("_server_api_up")
def test_create_experiment_duration_hits_quota(
    user1_client: UserClient,
    sample_target_config: TargetConfig,
) -> None:
    _xp = Experiment(
        name="test-experiment",
        duration=server_config.quota_default_duration + timedelta(seconds=5),
        target_configs=[sample_target_config],
    )
    assert user1_client.create_experiment(_xp) is None


@pytest.mark.usefixtures("_server_api_up")
def test_create_experiment_duration_with_valid_quota(
    user1_client: UserClient,
    admin_client: AdminClient,
    sample_target_config: TargetConfig,
) -> None:
    admin_client.extend_quota(
        account_email=user1_client._cfg.account_email,  # noqa: SLF001
        duration=timedelta(hours=60),
        expire_date=local_now() + timedelta(minutes=5),
    )
    _xp = Experiment(
        name="test-experiment",
        duration=server_config.quota_default_duration + timedelta(seconds=5),
        target_configs=[sample_target_config],
    )
    assert user1_client.create_experiment(_xp) is not None


# ###############################################################################
# GET
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_get_experiment_by_id(user1_client: UserClient) -> None:
    uids = user1_client.list_experiments()
    assert len(uids) > 0
    xp = user1_client.get_experiment(uids[0])
    assert isinstance(xp, Experiment)


@pytest.mark.usefixtures("_server_api_up")
def test_get_deleted_experiment_fails(user1_client: UserClient) -> None:
    uids = user1_client.list_experiments()
    assert len(uids) > 0
    xp = user1_client.get_experiment(uids[0])
    assert isinstance(xp, Experiment)
    assert user1_client.delete_experiment(uids[0])
    assert user1_client.get_experiment(uids[0]) is None


@pytest.mark.usefixtures("_server_api_up")
def test_get_experiment_is_authenticated(
    user1_client: UserClient, unconfirmed_client: UserClient
) -> None:
    uids = user1_client.list_experiments()
    assert len(uids) > 0
    assert unconfirmed_client.get_experiment(uids[0]) is None


@pytest.mark.usefixtures("_server_api_up")
def test_get_experiment_is_private(user1_client: UserClient, user2_client: UserClient) -> None:
    uids = user1_client.list_experiments()
    assert len(uids) > 0
    assert user2_client.get_experiment(uids[0]) is None


@pytest.mark.usefixtures("_server_api_up")
def test_get_experiments_as_admin(user1_client: UserClient, admin_client: AdminClient) -> None:
    uids = user1_client.list_experiments()
    assert len(uids) > 0
    xp = admin_client.get_experiment(uids[0])
    assert isinstance(xp, Experiment)


# ###############################################################################
# GET STATE
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_state_of_created_experiments(
    user1_client: UserClient, sample_experiment: Experiment
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid is not None
    state = user1_client.get_experiment_state(uid)
    assert state == "created"


@pytest.mark.usefixtures("_server_api_up")
def test_state_of_scheduled_experiment(
    user1_client: UserClient, sample_experiment: Experiment
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid is not None
    success = user1_client.schedule_experiment(uid)
    assert success
    state = user1_client.get_experiment_state(uid)
    assert state == "scheduled"


@pytest.mark.usefixtures("_server_api_up")
def test_state_of_running_experiment(user1_client: UserClient, running_experiment_id: UUID) -> None:
    state = user1_client.get_experiment_state(running_experiment_id)
    assert state == "running"


@pytest.mark.usefixtures("_server_api_up")
def test_state_of_finished_experiment(
    user1_client: UserClient, finished_experiment_id: UUID
) -> None:
    state = user1_client.get_experiment_state(finished_experiment_id)
    assert state == "finished"


@pytest.mark.usefixtures("_server_api_up")
def test_state_of_deleted_experiment_fails(
    user1_client: UserClient, finished_experiment_id: UUID
) -> None:
    state = user1_client.get_experiment_state(finished_experiment_id)
    assert state == "finished"
    success = user1_client.delete_experiment(finished_experiment_id)
    assert success
    state = user1_client.get_experiment_state(finished_experiment_id)
    assert state is None


@pytest.mark.usefixtures("_server_api_up")
def test_state_of_experiment_is_authenticated(
    user1_client: UserClient, unconfirmed_client: UserClient, sample_experiment: Experiment
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid is not None
    state = unconfirmed_client.get_experiment_state(uid)
    assert state is None


@pytest.mark.usefixtures("_server_api_up")
def test_state_of_experiment_is_private(
    user1_client: UserClient, sample_experiment: Experiment, user2_client: UserClient
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid is not None
    state = user2_client.get_experiment_state(uid)
    assert state is None


@pytest.mark.usefixtures("_server_api_up")
def test_state_of_experiments_as_admin(user1_client: UserClient, admin_client: AdminClient) -> None:
    uids = user1_client.list_experiments()
    assert len(uids) > 0
    state = admin_client.get_experiment_state(uids[0])
    assert state is not None


# ###############################################################################
# GET STATS
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_statistics_of_created_experiments(
    user1_client: UserClient, sample_experiment: Experiment
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid is not None
    stats = user1_client.get_experiment_statistics(uid)
    assert stats is not None


@pytest.mark.usefixtures("_server_api_up")
def test_statistics_of_scheduled_experiment(
    user1_client: UserClient, sample_experiment: Experiment
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid is not None
    success = user1_client.schedule_experiment(uid)
    assert success
    stats = user1_client.get_experiment_statistics(uid)
    assert stats is not None


@pytest.mark.usefixtures("_server_api_up")
def test_statistics_of_running_experiment(
    user1_client: UserClient, running_experiment_id: UUID
) -> None:
    stats = user1_client.get_experiment_statistics(running_experiment_id)
    assert stats is not None


@pytest.mark.usefixtures("_server_api_up")
def test_statistics_of_finished_experiment(
    user1_client: UserClient, finished_experiment_id: UUID
) -> None:
    stats = user1_client.get_experiment_statistics(finished_experiment_id)
    assert stats is not None


@pytest.mark.usefixtures("_server_api_up")
def test_statistics_of_deleted_experiment(
    user1_client: UserClient, finished_experiment_id: UUID
) -> None:
    success = user1_client.delete_experiment(finished_experiment_id)
    assert success
    stats = user1_client.get_experiment_statistics(finished_experiment_id)
    assert stats is not None


@pytest.mark.usefixtures("_server_api_up")
def test_statistics_of_experiment_is_authenticated(
    user1_client: UserClient, unconfirmed_client: UserClient, sample_experiment: Experiment
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid is not None
    state = unconfirmed_client.get_experiment_state(uid)
    assert state is None


@pytest.mark.usefixtures("_server_api_up")
def test_statistics_of_experiment_is_private(
    user1_client: UserClient, sample_experiment: Experiment, user2_client: UserClient
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid is not None
    state = user2_client.get_experiment_state(uid)
    assert state is None


@pytest.mark.usefixtures("_server_api_up")
def test_statistics_of_experiments_as_admin(
    user1_client: UserClient, admin_client: AdminClient
) -> None:
    uids = user1_client.list_experiments()
    assert len(uids) > 0
    state = admin_client.get_experiment_state(uids[0])
    assert state is not None


# ###############################################################################
# Schedule
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_schedule_experiment(user1_client: UserClient, sample_experiment: Experiment) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid is not None
    success = user1_client.schedule_experiment(uid)
    assert success
    state = user1_client.get_experiment_state(uid)
    assert state == "scheduled"


@pytest.mark.usefixtures("_server_api_up")
def test_schedule_scheduled_experiment_is_rejected(
    user1_client: UserClient, sample_experiment: Experiment
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid is not None
    success = user1_client.schedule_experiment(uid)
    assert success
    success = user1_client.schedule_experiment(uid)
    assert not success
    state = user1_client.get_experiment_state(uid)
    assert state == "scheduled"


@pytest.mark.usefixtures("_server_api_up")
def test_schedule_running_experiment_is_rejected(
    user1_client: UserClient, running_experiment_id: UUID
) -> None:
    success = user1_client.schedule_experiment(running_experiment_id)
    assert not success
    state = user1_client.get_experiment_state(running_experiment_id)
    assert state == "running"


@pytest.mark.usefixtures("_server_api_up")
def test_schedule_finished_experiment_is_rejected(
    user1_client: UserClient, finished_experiment_id: UUID
) -> None:
    success = user1_client.schedule_experiment(finished_experiment_id)
    assert not success
    state = user1_client.get_experiment_state(finished_experiment_id)
    assert state == "finished"


@pytest.mark.usefixtures("_server_api_up")
def test_schedule_experiment_is_authenticated(
    user1_client: UserClient, sample_experiment: Experiment, unconfirmed_client: UserClient
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid is not None
    success = unconfirmed_client.schedule_experiment(uid)
    assert not success
    state = user1_client.get_experiment_state(uid)
    assert state == "created"


@pytest.mark.usefixtures("_server_api_up")
def test_schedule_experiment_is_private(
    user1_client: UserClient, sample_experiment: Experiment, user2_client: UserClient
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid is not None
    success = user2_client.schedule_experiment(uid)
    assert not success
    state = user1_client.get_experiment_state(uid)
    assert state == "created"


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_schedule_experiment_as_admin(
    user1_client: UserClient, sample_experiment: Experiment, admin_client: AdminClient
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid is not None
    success = admin_client.schedule_experiment(uid)
    assert success
    state = user1_client.get_experiment_state(uid)
    assert state == "scheduled"


# ###############################################################################
# Download
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_download_created_experiment_is_rejected(
    user1_client: UserClient, sample_experiment: Experiment, tmp_path: Path
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid
    success = user1_client.download_experiment(uid, tmp_path)
    assert not success


@pytest.mark.usefixtures("_server_api_up")
def test_download_scheduled_experiment_is_rejected(
    user1_client: UserClient, sample_experiment: Experiment, tmp_path: Path
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid
    success = user1_client.schedule_experiment(uid)
    assert success
    success = user1_client.download_experiment(uid, tmp_path)
    assert not success


@pytest.mark.usefixtures("_server_api_up")
def test_download_running_experiment_is_rejected(
    user1_client: UserClient, running_experiment_id: UUID, tmp_path: Path
) -> None:
    success = user1_client.download_experiment(running_experiment_id, tmp_path)
    assert not success


@pytest.mark.usefixtures("_server_api_up")
def test_download_finished_experiment(
    user1_client: UserClient, finished_experiment_id: UUID, tmp_path: Path
) -> None:
    state = user1_client.get_experiment_state(finished_experiment_id)
    assert state == "finished"
    success = user1_client.download_experiment(finished_experiment_id, tmp_path)
    assert success


@pytest.mark.usefixtures("_server_api_up")
def test_download_deleted_experiment(
    user1_client: UserClient, finished_experiment_id: UUID, tmp_path: Path
) -> None:
    state = user1_client.get_experiment_state(finished_experiment_id)
    assert state == "finished"
    success = user1_client.delete_experiment(finished_experiment_id)
    assert success
    success = user1_client.download_experiment(finished_experiment_id, tmp_path)
    assert not success


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_download_finished_experiment_is_authenticated(
    user1_client: UserClient,
    unconfirmed_client: UserClient,
    finished_experiment_id: UUID,
    tmp_path: Path,
) -> None:
    state = user1_client.get_experiment_state(finished_experiment_id)
    assert state == "finished"
    success = unconfirmed_client.download_experiment(finished_experiment_id, tmp_path)
    assert not success


@pytest.mark.usefixtures("_server_api_up")
def test_download_finished_experiment_is_private_and_authenticated(
    user1_client: UserClient, user2_client: UserClient, finished_experiment_id: UUID, tmp_path: Path
) -> None:
    state = user1_client.get_experiment_state(finished_experiment_id)
    assert state == "finished"
    success = user2_client.download_experiment(finished_experiment_id, tmp_path)
    assert not success


@pytest.mark.usefixtures("_server_api_up")
def test_download_finished_experiment_as_admin(
    user1_client: UserClient,
    admin_client: AdminClient,
    finished_experiment_id: UUID,
    tmp_path: Path,
) -> None:
    state = user1_client.get_experiment_state(finished_experiment_id)
    assert state == "finished"
    success = admin_client.download_experiment(finished_experiment_id, tmp_path)
    assert success


# ###############################################################################
# DELETE
# ###############################################################################


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_delete_nonexisting_experiments_is_rejected(user1_client: UserClient) -> None:
    success = user1_client.delete_experiment(UUID("{12345678-1234-5678-1234-567812345678}"))
    assert not success


@pytest.mark.usefixtures("_server_api_up")
def test_delete_created_experiments(
    user1_client: UserClient, sample_experiment: Experiment
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid
    success = user1_client.delete_experiment(uid)
    assert success


@pytest.mark.usefixtures("_server_api_up")
def test_delete_scheduled_experiments(
    user1_client: UserClient, sample_experiment: Experiment
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid
    success = user1_client.schedule_experiment(uid)
    assert success
    success = user1_client.delete_experiment(uid)
    assert success


@pytest.mark.usefixtures("_server_api_up")
def test_delete_running_experiment_is_rejected(
    user1_client: UserClient, running_experiment_id: UUID
) -> None:
    success = user1_client.delete_experiment(running_experiment_id)
    assert not success


@pytest.mark.usefixtures("_server_api_up")
def test_delete_finished_experiments(
    user1_client: UserClient, finished_experiment_id: UUID
) -> None:
    success = user1_client.delete_experiment(finished_experiment_id)
    assert success


@pytest.mark.usefixtures("_primed_database")
@pytest.mark.usefixtures("_server_api_up")
def test_delete_experiment_is_authenticated(
    user1_client: UserClient, unconfirmed_client: UserClient, sample_experiment: Experiment
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid is not None
    success = unconfirmed_client.delete_experiment(uid)
    assert not success
    state = user1_client.get_experiment_state(uid)
    assert state is not None


@pytest.mark.usefixtures("_server_api_up")
def test_delete_experiment_is_private(
    user1_client: UserClient, user2_client: UserClient, sample_experiment: Experiment
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid is not None
    success = user2_client.delete_experiment(uid)
    assert not success
    state = user1_client.get_experiment_state(uid)
    assert state is not None


@pytest.mark.usefixtures("_server_api_up")
def test_delete_experiment_as_admin(
    user1_client: UserClient, admin_client: UserClient, sample_experiment: Experiment
) -> None:
    uid = user1_client.create_experiment(sample_experiment)
    assert uid is not None
    success = admin_client.delete_experiment(uid)
    assert success
    state = user1_client.get_experiment_state(uid)
    assert state is None
