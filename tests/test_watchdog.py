"""Tests for cronwatcher.watchdog."""

from __future__ import annotations

import datetime
import sqlite3

import pytest

from cronwatcher.db import init_db, get_connection
from cronwatcher.watchdog import find_hung_jobs, mark_hung_jobs


@pytest.fixture()
def tmp_db(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def _now() -> datetime.datetime:
    return datetime.datetime.utcnow()


def _insert_run(
    db_path: str,
    job_name: str,
    started_at: datetime.datetime,
    finished_at: datetime.datetime | None = None,
    exit_code: int | None = None,
) -> int:
    con = get_connection(db_path)
    cur = con.execute(
        "INSERT INTO runs (job_name, started_at, finished_at, exit_code) VALUES (?,?,?,?)",
        (job_name, started_at.isoformat(),
         finished_at.isoformat() if finished_at else None, exit_code),
    )
    con.commit()
    run_id = cur.lastrowid
    con.close()
    return run_id


def test_find_hung_jobs_empty(tmp_db):
    assert find_hung_jobs(tmp_db) == []


def test_find_hung_jobs_detects_old_unfinished(tmp_db):
    ref = _now()
    old_start = ref - datetime.timedelta(hours=2)
    _insert_run(tmp_db, "backup", old_start)

    result = find_hung_jobs(tmp_db, timeout_seconds=3600, reference_time=ref)
    assert len(result) == 1
    assert result[0].job_name == "backup"
    assert result[0].running_seconds >= 7200 - 1


def test_find_hung_jobs_ignores_recent(tmp_db):
    ref = _now()
    recent_start = ref - datetime.timedelta(minutes=10)
    _insert_run(tmp_db, "quick", recent_start)

    result = find_hung_jobs(tmp_db, timeout_seconds=3600, reference_time=ref)
    assert result == []


def test_find_hung_jobs_ignores_finished(tmp_db):
    ref = _now()
    old_start = ref - datetime.timedelta(hours=3)
    old_end = ref - datetime.timedelta(hours=2)
    _insert_run(tmp_db, "done", old_start, finished_at=old_end, exit_code=0)

    result = find_hung_jobs(tmp_db, timeout_seconds=3600, reference_time=ref)
    assert result == []


def test_mark_hung_jobs_updates_db(tmp_db):
    ref = _now()
    old_start = ref - datetime.timedelta(hours=5)
    run_id = _insert_run(tmp_db, "etl", old_start)

    marked = mark_hung_jobs(tmp_db, timeout_seconds=3600, reference_time=ref)
    assert len(marked) == 1
    assert marked[0].run_id == run_id

    con = get_connection(tmp_db)
    row = con.execute(
        "SELECT exit_code, stderr, finished_at FROM runs WHERE id = ?", (run_id,)
    ).fetchone()
    con.close()
    assert row["exit_code"] == -1
    assert "watchdog" in row["stderr"]
    assert row["finished_at"] is not None


def test_mark_hung_jobs_returns_empty_when_none(tmp_db):
    result = mark_hung_jobs(tmp_db)
    assert result == []
