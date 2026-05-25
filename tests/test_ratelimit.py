"""Tests for cronwatcher.ratelimit."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from cronwatcher.ratelimit import (
    count_recent_alerts,
    is_rate_limited,
    prune_old_entries,
    record_rate_limit_alert,
)


@pytest.fixture()
def tmp_db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    yield conn
    conn.close()


def _dt(offset_seconds: int = 0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)


# ---------------------------------------------------------------------------
# count_recent_alerts
# ---------------------------------------------------------------------------

def test_count_recent_alerts_empty(tmp_db):
    assert count_recent_alerts(tmp_db, "backup", 3600) == 0


def test_count_recent_alerts_within_window(tmp_db):
    record_rate_limit_alert(tmp_db, "backup", now=_dt(-10))
    record_rate_limit_alert(tmp_db, "backup", now=_dt(-20))
    assert count_recent_alerts(tmp_db, "backup", 3600) == 2


def test_count_recent_alerts_excludes_old(tmp_db):
    record_rate_limit_alert(tmp_db, "backup", now=_dt(-7200))  # 2 h ago
    record_rate_limit_alert(tmp_db, "backup", now=_dt(-30))    # recent
    assert count_recent_alerts(tmp_db, "backup", 3600) == 1


def test_count_recent_alerts_isolates_jobs(tmp_db):
    record_rate_limit_alert(tmp_db, "job_a", now=_dt(-10))
    record_rate_limit_alert(tmp_db, "job_b", now=_dt(-10))
    assert count_recent_alerts(tmp_db, "job_a", 3600) == 1
    assert count_recent_alerts(tmp_db, "job_b", 3600) == 1


# ---------------------------------------------------------------------------
# record_rate_limit_alert
# ---------------------------------------------------------------------------

def test_record_returns_positive_id(tmp_db):
    row_id = record_rate_limit_alert(tmp_db, "myjob")
    assert row_id > 0


def test_record_increments_id(tmp_db):
    id1 = record_rate_limit_alert(tmp_db, "myjob")
    id2 = record_rate_limit_alert(tmp_db, "myjob")
    assert id2 > id1


# ---------------------------------------------------------------------------
# is_rate_limited
# ---------------------------------------------------------------------------

def test_not_rate_limited_when_below_quota(tmp_db):
    record_rate_limit_alert(tmp_db, "job", now=_dt(-10))
    assert not is_rate_limited(tmp_db, "job", 3600, max_alerts=5)


def test_rate_limited_when_quota_reached(tmp_db):
    for _ in range(3):
        record_rate_limit_alert(tmp_db, "job", now=_dt(-10))
    assert is_rate_limited(tmp_db, "job", 3600, max_alerts=3)


def test_not_rate_limited_when_window_zero(tmp_db):
    for _ in range(10):
        record_rate_limit_alert(tmp_db, "job")
    assert not is_rate_limited(tmp_db, "job", window_seconds=0, max_alerts=1)


def test_not_rate_limited_when_max_alerts_zero(tmp_db):
    record_rate_limit_alert(tmp_db, "job")
    assert not is_rate_limited(tmp_db, "job", window_seconds=3600, max_alerts=0)


# ---------------------------------------------------------------------------
# prune_old_entries
# ---------------------------------------------------------------------------

def test_prune_removes_old_entries(tmp_db):
    record_rate_limit_alert(tmp_db, "job", now=_dt(-7200))
    record_rate_limit_alert(tmp_db, "job", now=_dt(-30))
    removed = prune_old_entries(tmp_db, window_seconds=3600)
    assert removed == 1
    assert count_recent_alerts(tmp_db, "job", 3600) == 1


def test_prune_returns_zero_when_nothing_old(tmp_db):
    record_rate_limit_alert(tmp_db, "job", now=_dt(-10))
    assert prune_old_entries(tmp_db, window_seconds=3600) == 0
