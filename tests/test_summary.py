"""Tests for cronwatcher.summary."""

import sqlite3
import pytest
from datetime import datetime, timezone

from cronwatcher.db import init_db
from cronwatcher.summary import (
    JobSummary,
    summarise_job,
    summarise_all_jobs,
    format_summary_table,
)


@pytest.fixture()
def tmp_db(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def _insert_run(db_path: str, job_name: str, exit_code: int, started_at: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        INSERT INTO runs (job_name, started_at, finished_at, exit_code, stdout, stderr)
        VALUES (?, ?, ?, ?, '', '')
        """,
        (job_name, started_at, started_at, exit_code),
    )
    conn.commit()
    conn.close()


def test_summarise_job_empty(tmp_db):
    s = summarise_job(tmp_db, "missing-job")
    assert s.job_name == "missing-job"
    assert s.total_runs == 0
    assert s.successful_runs == 0
    assert s.failed_runs == 0
    assert s.last_run_at is None
    assert s.last_exit_code is None


def test_summarise_job_counts(tmp_db):
    _insert_run(tmp_db, "backup", 0, "2024-01-01T00:00:00")
    _insert_run(tmp_db, "backup", 0, "2024-01-02T00:00:00")
    _insert_run(tmp_db, "backup", 1, "2024-01-03T00:00:00")

    s = summarise_job(tmp_db, "backup")
    assert s.total_runs == 3
    assert s.successful_runs == 2
    assert s.failed_runs == 1


def test_failure_rate(tmp_db):
    _insert_run(tmp_db, "job", 1, "2024-01-01T00:00:00")
    _insert_run(tmp_db, "job", 1, "2024-01-02T00:00:00")
    _insert_run(tmp_db, "job", 0, "2024-01-03T00:00:00")

    s = summarise_job(tmp_db, "job")
    assert abs(s.failure_rate - 2 / 3) < 1e-9
    assert abs(s.success_rate - 1 / 3) < 1e-9


def test_summarise_all_jobs(tmp_db):
    _insert_run(tmp_db, "alpha", 0, "2024-01-01T00:00:00")
    _insert_run(tmp_db, "beta", 1, "2024-01-01T00:00:00")

    summaries = summarise_all_jobs(tmp_db)
    names = [s.job_name for s in summaries]
    assert "alpha" in names
    assert "beta" in names


def test_summarise_all_jobs_empty(tmp_db):
    assert summarise_all_jobs(tmp_db) == []


def test_format_summary_table_no_data():
    result = format_summary_table([])
    assert result == "No job runs recorded."


def test_format_summary_table_contains_job_name(tmp_db):
    _insert_run(tmp_db, "my-cron-job", 0, "2024-06-01T12:00:00")
    summaries = summarise_all_jobs(tmp_db)
    table = format_summary_table(summaries)
    assert "my-cron-job" in table
    assert "0.0%" in table
