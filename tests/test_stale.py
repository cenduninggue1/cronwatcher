"""Tests for cronwatcher.stale."""

from __future__ import annotations

import datetime
import sqlite3
import pytest

from cronwatcher.db import init_db, get_connection
from cronwatcher.stale import find_stale_jobs, get_last_run_time, StaleJob
from cronwatcher.config import JobConfig


@pytest.fixture()
def tmp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    return db_path


def _make_job(name: str, stale_after_minutes: int | None = None) -> JobConfig:
    return JobConfig(
        name=name,
        command="echo hi",
        schedule="* * * * *",
        stale_after_minutes=stale_after_minutes,
    )


def _insert_run(db_path: str, job_name: str, started_at: datetime.datetime) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO runs (job_name, started_at) VALUES (?, ?)",
            (job_name, started_at.isoformat()),
        )


NOW = datetime.datetime(2024, 6, 1, 12, 0, 0)


def test_get_last_run_none_when_no_runs(tmp_db):
    assert get_last_run_time(tmp_db, "myjob") is None


def test_get_last_run_returns_latest(tmp_db):
    older = NOW - datetime.timedelta(hours=2)
    newer = NOW - datetime.timedelta(hours=1)
    _insert_run(tmp_db, "myjob", older)
    _insert_run(tmp_db, "myjob", newer)
    result = get_last_run_time(tmp_db, "myjob")
    assert result == newer


def test_no_stale_without_threshold(tmp_db):
    job = _make_job("nothreshold", stale_after_minutes=None)
    result = find_stale_jobs(tmp_db, [job], now=NOW)
    assert result == []


def test_never_run_job_is_stale(tmp_db):
    job = _make_job("neverrun", stale_after_minutes=60)
    result = find_stale_jobs(tmp_db, [job], now=NOW)
    assert len(result) == 1
    s = result[0]
    assert s.job_name == "neverrun"
    assert s.last_run_at is None
    assert s.minutes_overdue == 60.0


def test_recently_run_job_is_not_stale(tmp_db):
    job = _make_job("fresh", stale_after_minutes=60)
    _insert_run(tmp_db, "fresh", NOW - datetime.timedelta(minutes=30))
    result = find_stale_jobs(tmp_db, [job], now=NOW)
    assert result == []


def test_overdue_job_is_stale(tmp_db):
    job = _make_job("overdue", stale_after_minutes=60)
    _insert_run(tmp_db, "overdue", NOW - datetime.timedelta(minutes=90))
    result = find_stale_jobs(tmp_db, [job], now=NOW)
    assert len(result) == 1
    assert result[0].minutes_overdue == 30.0


def test_multiple_jobs_mixed(tmp_db):
    fresh = _make_job("fresh", stale_after_minutes=60)
    stale = _make_job("stale", stale_after_minutes=60)
    no_thresh = _make_job("nothresh", stale_after_minutes=None)
    _insert_run(tmp_db, "fresh", NOW - datetime.timedelta(minutes=10))
    _insert_run(tmp_db, "stale", NOW - datetime.timedelta(minutes=120))
    result = find_stale_jobs(tmp_db, [fresh, stale, no_thresh], now=NOW)
    assert len(result) == 1
    assert result[0].job_name == "stale"
