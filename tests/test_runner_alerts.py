"""Integration-style tests verifying runner triggers alerts on failure."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cronwatcher.config import AlertConfig, JobConfig
from cronwatcher.db import get_connection, init_db
from cronwatcher.runner import run_job


@pytest.fixture()
def tmp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    return db_path


@pytest.fixture()
def alert_cfg() -> AlertConfig:
    return AlertConfig(
        enabled=True,
        to_addresses=["ops@example.com"],
    )


@pytest.fixture()
def failing_job() -> JobConfig:
    return JobConfig(name="fail_job", command="exit 1", schedule="* * * * *", alert_on_failure=True)


@pytest.fixture()
def silent_job() -> JobConfig:
    """Job that fails but has alert_on_failure=False."""
    return JobConfig(name="silent_job", command="exit 2", schedule="* * * * *", alert_on_failure=False)


def test_alert_dispatched_on_failure(tmp_db, alert_cfg, failing_job):
    with patch("cronwatcher.runner.dispatch_alert", return_value=True) as mock_alert:
        result = run_job(failing_job, tmp_db, alert_cfg)

    assert result.exit_code != 0
    mock_alert.assert_called_once()
    _, kwargs_job, kwargs_code = mock_alert.call_args[0][:3]
    assert kwargs_job == "fail_job"


def test_alert_not_dispatched_on_success(tmp_db, alert_cfg):
    job = JobConfig(name="ok_job", command="echo hi", schedule="* * * * *", alert_on_failure=True)
    with patch("cronwatcher.runner.dispatch_alert") as mock_alert:
        result = run_job(job, tmp_db, alert_cfg)

    assert result.exit_code == 0
    mock_alert.assert_not_called()


def test_alert_suppressed_when_flag_false(tmp_db, alert_cfg, silent_job):
    with patch("cronwatcher.runner.dispatch_alert") as mock_alert:
        result = run_job(silent_job, tmp_db, alert_cfg)

    assert result.exit_code != 0
    mock_alert.assert_not_called()
