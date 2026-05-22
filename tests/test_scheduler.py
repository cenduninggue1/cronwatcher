"""Tests for cronwatcher.scheduler."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.config import AlertConfig, Config, JobConfig
from cronwatcher.scheduler import jobs_due, run_due_jobs


def _job(name: str, schedule: str) -> JobConfig:
    return JobConfig(name=name, schedule=schedule, command=f"echo {name}")


# ---------------------------------------------------------------------------
# jobs_due
# ---------------------------------------------------------------------------

def test_jobs_due_returns_matching_job():
    # Every-minute schedule should always be due.
    job = _job("every-min", "* * * * *")
    now = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert job in jobs_due([job], now=now)


def test_jobs_due_skips_non_matching_job():
    # Schedule fires only at midnight; use noon as 'now'.
    job = _job("midnight", "0 0 * * *")
    now = datetime(2024, 6, 1, 12, 30, 0, tzinfo=timezone.utc)
    assert job not in jobs_due([job], now=now)


def test_jobs_due_handles_invalid_schedule(caplog):
    job = _job("bad", "not-a-cron")
    now = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    result = jobs_due([job], now=now)
    assert result == []
    assert "Invalid schedule" in caplog.text


def test_jobs_due_multiple_jobs():
    every_min = _job("a", "* * * * *")
    midnight = _job("b", "0 0 * * *")
    now = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    due = jobs_due([every_min, midnight], now=now)
    assert every_min in due
    assert midnight not in due


# ---------------------------------------------------------------------------
# run_due_jobs
# ---------------------------------------------------------------------------

def _make_config(tmp_path, jobs):
    return Config(
        database=str(tmp_path / "cron.db"),
        jobs=jobs,
        alert=AlertConfig(enabled=False),
    )


def test_run_due_jobs_calls_run_job(tmp_path):
    job = _job("tick", "* * * * *")
    cfg = _make_config(tmp_path, [job])

    with patch("cronwatcher.scheduler.run_job") as mock_run, \
         patch("cronwatcher.scheduler._utcnow",
               return_value=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)):
        run_due_jobs(cfg)
        mock_run.assert_called_once()
        call_job = mock_run.call_args[0][0]
        assert call_job.name == "tick"


def test_run_due_jobs_no_due_jobs(tmp_path, caplog):
    job = _job("midnight", "0 0 * * *")
    cfg = _make_config(tmp_path, [job])

    with patch("cronwatcher.scheduler.run_job") as mock_run, \
         patch("cronwatcher.scheduler._utcnow",
               return_value=datetime(2024, 6, 1, 12, 30, 0, tzinfo=timezone.utc)):
        run_due_jobs(cfg)
        mock_run.assert_not_called()
