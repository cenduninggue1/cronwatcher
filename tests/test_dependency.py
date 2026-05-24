"""Tests for cronwatcher.dependency."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from cronwatcher.db import init_db, get_connection
from cronwatcher.dependency import (
    get_last_success,
    check_dependency,
    all_dependencies_satisfied,
)


@pytest.fixture()
def tmp_db(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _insert_run(db_path: str, job_name: str, exit_code: int, finished_at: datetime | None):
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO runs (job_name, started_at, finished_at, exit_code, stdout, stderr)
            VALUES (?, ?, ?, ?, '', '')
            """,
            (
                job_name,
                _now().isoformat(),
                finished_at.isoformat() if finished_at else None,
                exit_code,
            ),
        )


def test_get_last_success_none_when_empty(tmp_db):
    assert get_last_success(tmp_db, "backup") is None


def test_get_last_success_ignores_failures(tmp_db):
    _insert_run(tmp_db, "backup", 1, _now())
    assert get_last_success(tmp_db, "backup") is None


def test_get_last_success_returns_latest(tmp_db):
    older = _now() - timedelta(hours=2)
    newer = _now() - timedelta(minutes=5)
    _insert_run(tmp_db, "backup", 0, older)
    _insert_run(tmp_db, "backup", 0, newer)
    result = get_last_success(tmp_db, "backup")
    assert result is not None
    assert abs((result - newer).total_seconds()) < 2


def test_check_dependency_unsatisfied_when_no_runs(tmp_db):
    res = check_dependency(tmp_db, "etl", max_age_seconds=3600)
    assert res.satisfied is False
    assert "never succeeded" in res.reason


def test_check_dependency_satisfied_with_recent_success(tmp_db):
    _insert_run(tmp_db, "etl", 0, _now() - timedelta(minutes=10))
    res = check_dependency(tmp_db, "etl", max_age_seconds=3600)
    assert res.satisfied is True
    assert res.reason == "ok"


def test_check_dependency_unsatisfied_when_too_old(tmp_db):
    _insert_run(tmp_db, "etl", 0, _now() - timedelta(hours=3))
    res = check_dependency(tmp_db, "etl", max_age_seconds=3600)
    assert res.satisfied is False
    assert "limit 3600s" in res.reason


def test_check_dependency_no_age_limit_accepts_old_success(tmp_db):
    _insert_run(tmp_db, "etl", 0, _now() - timedelta(days=30))
    res = check_dependency(tmp_db, "etl", max_age_seconds=None)
    assert res.satisfied is True


def test_all_dependencies_satisfied_all_ok(tmp_db):
    _insert_run(tmp_db, "a", 0, _now() - timedelta(minutes=1))
    _insert_run(tmp_db, "b", 0, _now() - timedelta(minutes=2))
    ok, results = all_dependencies_satisfied(tmp_db, ["a", "b"], max_age_seconds=3600)
    assert ok is True
    assert all(r.satisfied for r in results)


def test_all_dependencies_satisfied_one_fails(tmp_db):
    _insert_run(tmp_db, "a", 0, _now() - timedelta(minutes=1))
    # "b" never ran
    ok, results = all_dependencies_satisfied(tmp_db, ["a", "b"], max_age_seconds=3600)
    assert ok is False
    assert results[0].satisfied is True
    assert results[1].satisfied is False
