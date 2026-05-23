"""Tests for cronwatcher.retention."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from cronwatcher.db import init_db
from cronwatcher.retention import prune_runs


@pytest.fixture()
def tmp_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    return db_path


def _insert_run(
    db_path: str,
    job_name: str,
    started_at: datetime,
    exit_code: int = 0,
) -> None:
    conn = sqlite3.connect(db_path)
    finished_at = started_at + timedelta(seconds=1)
    conn.execute(
        """
        INSERT INTO job_runs (job_name, started_at, finished_at, exit_code, stdout, stderr)
        VALUES (?, ?, ?, ?, '', '')
        """,
        (
            job_name,
            started_at.strftime("%Y-%m-%dT%H:%M:%S"),
            finished_at.strftime("%Y-%m-%dT%H:%M:%S"),
            exit_code,
        ),
    )
    conn.commit()
    conn.close()


def _count(db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    n = conn.execute("SELECT COUNT(*) FROM job_runs").fetchone()[0]
    conn.close()
    return n


def test_prune_no_policy_deletes_nothing(tmp_db: str) -> None:
    now = datetime.now(timezone.utc)
    _insert_run(tmp_db, "job_a", now - timedelta(days=100))
    assert prune_runs(tmp_db) == 0
    assert _count(tmp_db) == 1


def test_prune_by_age_removes_old_rows(tmp_db: str) -> None:
    now = datetime.now(timezone.utc)
    _insert_run(tmp_db, "job_a", now - timedelta(days=10))
    _insert_run(tmp_db, "job_a", now - timedelta(days=2))
    deleted = prune_runs(tmp_db, max_age_days=5)
    assert deleted == 1
    assert _count(tmp_db) == 1


def test_prune_by_age_keeps_recent_rows(tmp_db: str) -> None:
    now = datetime.now(timezone.utc)
    _insert_run(tmp_db, "job_a", now - timedelta(hours=1))
    deleted = prune_runs(tmp_db, max_age_days=30)
    assert deleted == 0
    assert _count(tmp_db) == 1


def test_prune_by_max_rows_keeps_newest(tmp_db: str) -> None:
    now = datetime.now(timezone.utc)
    for i in range(5):
        _insert_run(tmp_db, "job_a", now - timedelta(hours=5 - i))
    deleted = prune_runs(tmp_db, max_rows_per_job=3)
    assert deleted == 2
    assert _count(tmp_db) == 3


def test_prune_by_max_rows_per_job_independent(tmp_db: str) -> None:
    now = datetime.now(timezone.utc)
    for i in range(4):
        _insert_run(tmp_db, "job_a", now - timedelta(hours=4 - i))
    for i in range(4):
        _insert_run(tmp_db, "job_b", now - timedelta(hours=4 - i))
    deleted = prune_runs(tmp_db, max_rows_per_job=2)
    assert deleted == 4
    assert _count(tmp_db) == 4


def test_prune_combined_age_and_rows(tmp_db: str) -> None:
    now = datetime.now(timezone.utc)
    _insert_run(tmp_db, "job_a", now - timedelta(days=20))  # too old
    for i in range(4):
        _insert_run(tmp_db, "job_a", now - timedelta(hours=4 - i))  # recent
    deleted = prune_runs(tmp_db, max_age_days=10, max_rows_per_job=2)
    assert deleted == 1 + 2  # 1 old + 2 excess recent
    assert _count(tmp_db) == 2
