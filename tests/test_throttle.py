"""Tests for cronwatcher.throttle."""

from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from cronwatcher.db import get_connection, init_db
from cronwatcher.notifier import _ensure_table, record_alert
from cronwatcher.throttle import is_throttled, maybe_record_alert, reset_throttle


@pytest.fixture()
def tmp_db(tmp_path):
    path = str(tmp_path / "test.db")
    conn = get_connection(path)
    init_db(conn)
    _ensure_table(conn)
    return path


def _dt(minutes_ago: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)


# ---------------------------------------------------------------------------
# is_throttled
# ---------------------------------------------------------------------------

def test_not_throttled_when_no_alert_recorded(tmp_db):
    assert is_throttled(tmp_db, "backup", cooldown_minutes=30) is False


def test_not_throttled_when_cooldown_is_zero(tmp_db):
    conn = get_connection(tmp_db)
    record_alert(conn, "backup")
    assert is_throttled(tmp_db, "backup", cooldown_minutes=0) is False


def test_throttled_within_cooldown(tmp_db):
    conn = get_connection(tmp_db)
    record_alert(conn, "backup")
    # alert just recorded → within any positive cooldown
    assert is_throttled(tmp_db, "backup", cooldown_minutes=60) is True


def test_not_throttled_after_cooldown_expires(tmp_db):
    """Simulate an old alert by patching _utcnow in the throttle module."""
    conn = get_connection(tmp_db)
    record_alert(conn, "backup")
    # Make 'now' appear to be 90 minutes later
    future = datetime.now(timezone.utc) + timedelta(minutes=90)
    with patch("cronwatcher.throttle._utcnow", return_value=future):
        assert is_throttled(tmp_db, "backup", cooldown_minutes=60) is False


# ---------------------------------------------------------------------------
# maybe_record_alert
# ---------------------------------------------------------------------------

def test_maybe_record_alert_returns_true_first_time(tmp_db):
    assert maybe_record_alert(tmp_db, "deploy", cooldown_minutes=30) is True


def test_maybe_record_alert_returns_false_when_throttled(tmp_db):
    maybe_record_alert(tmp_db, "deploy", cooldown_minutes=30)
    assert maybe_record_alert(tmp_db, "deploy", cooldown_minutes=30) is False


def test_maybe_record_alert_different_jobs_independent(tmp_db):
    assert maybe_record_alert(tmp_db, "job_a", cooldown_minutes=30) is True
    assert maybe_record_alert(tmp_db, "job_b", cooldown_minutes=30) is True


# ---------------------------------------------------------------------------
# reset_throttle
# ---------------------------------------------------------------------------

def test_reset_throttle_removes_records(tmp_db):
    maybe_record_alert(tmp_db, "deploy", cooldown_minutes=30)
    removed = reset_throttle(tmp_db, "deploy")
    assert removed >= 1
    assert is_throttled(tmp_db, "deploy", cooldown_minutes=30) is False


def test_reset_throttle_returns_zero_when_nothing_to_remove(tmp_db):
    assert reset_throttle(tmp_db, "nonexistent") == 0
