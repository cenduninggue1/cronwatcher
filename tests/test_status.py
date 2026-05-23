"""Tests for cronwatcher.status."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from cronwatcher.db import init_db, get_connection
from cronwatcher.heartbeat import record_heartbeat
from cronwatcher.status import get_daemon_status, format_status, DaemonStatus


@pytest.fixture()
def tmp_db(tmp_path: Path) -> str:
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def _insert_run(conn: sqlite3.Connection, job_name: str, exit_code: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO runs (job_name, started_at, finished_at, exit_code, stdout, stderr) "
        "VALUES (?, ?, ?, ?, '', '')",
        (job_name, now, now, exit_code),
    )
    conn.commit()


def test_status_no_heartbeat(tmp_db: str) -> None:
    status = get_daemon_status(tmp_db, overdue_seconds=60)
    assert status.running is False
    assert status.last_heartbeat is None
    assert status.heartbeat_overdue is True
    assert status.total_jobs == 0
    assert status.healthy is False


def test_status_fresh_heartbeat(tmp_db: str) -> None:
    conn = get_connection(tmp_db)
    record_heartbeat(conn)
    conn.close()

    status = get_daemon_status(tmp_db, overdue_seconds=120)
    assert status.running is True
    assert status.heartbeat_overdue is False
    assert status.last_heartbeat is not None


def test_status_counts_failure_jobs(tmp_db: str) -> None:
    conn = get_connection(tmp_db)
    record_heartbeat(conn)
    _insert_run(conn, "backup", 0)
    _insert_run(conn, "backup", 1)
    _insert_run(conn, "cleanup", 0)
    conn.close()

    status = get_daemon_status(tmp_db, overdue_seconds=120)
    assert status.total_jobs == 2
    assert status.jobs_with_failures == 1
    assert status.healthy is False


def test_status_healthy_when_no_failures(tmp_db: str) -> None:
    conn = get_connection(tmp_db)
    record_heartbeat(conn)
    _insert_run(conn, "backup", 0)
    conn.close()

    status = get_daemon_status(tmp_db, overdue_seconds=120)
    assert status.healthy is True


def test_format_status_contains_key_fields(tmp_db: str) -> None:
    conn = get_connection(tmp_db)
    record_heartbeat(conn)
    conn.close()

    status = get_daemon_status(tmp_db, overdue_seconds=120)
    output = format_status(status)
    assert "Status" in output
    assert "heartbeat" in output.lower()
    assert "Tracked jobs" in output


def test_format_status_never_when_no_heartbeat(tmp_db: str) -> None:
    status = get_daemon_status(tmp_db)
    output = format_status(status)
    assert "never" in output
