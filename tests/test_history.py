"""Tests for cronwatcher.history query helpers."""

import pytest
from datetime import timezone

from cronwatcher.db import init_db, record_start, record_finish, get_connection
from cronwatcher.history import (
    get_recent_runs,
    get_failed_runs,
    get_last_run,
    JobRun,
)


@pytest.fixture
def tmp_db(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def _add_run(db_path, job_name, exit_code, stderr=""):
    run_id = record_start(db_path, job_name)
    record_finish(db_path, run_id, exit_code, stderr)
    return run_id


def test_get_last_run_none_when_empty(tmp_db):
    assert get_last_run(tmp_db, "backup") is None


def test_get_last_run_returns_most_recent(tmp_db):
    _add_run(tmp_db, "backup", 0)
    _add_run(tmp_db, "backup", 1, stderr="oops")
    run = get_last_run(tmp_db, "backup")
    assert run is not None
    assert run.exit_code == 1
    assert run.stderr == "oops"


def test_get_recent_runs_order(tmp_db):
    for code in [0, 0, 1]:
        _add_run(tmp_db, "sync", code)
    runs = get_recent_runs(tmp_db, "sync")
    assert len(runs) == 3
    # newest first — last inserted had exit_code=1
    assert runs[0].exit_code == 1


def test_get_recent_runs_limit(tmp_db):
    for _ in range(5):
        _add_run(tmp_db, "cleanup", 0)
    runs = get_recent_runs(tmp_db, "cleanup", limit=3)
    assert len(runs) == 3


def test_get_recent_runs_filters_by_job(tmp_db):
    _add_run(tmp_db, "jobA", 0)
    _add_run(tmp_db, "jobB", 1)
    runs = get_recent_runs(tmp_db, "jobA")
    assert all(r.job_name == "jobA" for r in runs)


def test_get_failed_runs_only_failures(tmp_db):
    _add_run(tmp_db, "alpha", 0)
    _add_run(tmp_db, "alpha", 2, stderr="err")
    _add_run(tmp_db, "beta", 1, stderr="fail")
    failed = get_failed_runs(tmp_db)
    assert len(failed) == 2
    assert all(r.exit_code != 0 for r in failed)


def test_job_run_succeeded_property(tmp_db):
    _add_run(tmp_db, "myjob", 0)
    run = get_last_run(tmp_db, "myjob")
    assert run.succeeded is True


def test_job_run_duration(tmp_db):
    _add_run(tmp_db, "myjob", 0)
    run = get_last_run(tmp_db, "myjob")
    assert run.duration_seconds is not None
    assert run.duration_seconds >= 0.0


def test_job_run_timestamps_are_utc(tmp_db):
    _add_run(tmp_db, "myjob", 0)
    run = get_last_run(tmp_db, "myjob")
    assert run.started_at.tzinfo == timezone.utc
    assert run.finished_at.tzinfo == timezone.utc
