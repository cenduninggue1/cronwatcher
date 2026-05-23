"""Tests for cronwatcher.notifier (alert throttling)."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from cronwatcher.notifier import (
    last_alert_time,
    record_alert,
    should_alert,
)


@pytest.fixture()
def tmp_db(tmp_path):
    db = str(tmp_path / "test.db")
    # init_db creates the core tables; notifier creates its own lazily
    from cronwatcher.db import init_db
    init_db(db)
    return db


def _dt(offset_minutes: int = 0) -> datetime:
    return datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=offset_minutes)


def test_last_alert_time_none_when_empty(tmp_db):
    assert last_alert_time(tmp_db, "backup") is None


def test_record_and_retrieve_alert(tmp_db):
    when = _dt()
    record_alert(tmp_db, "backup", when=when)
    result = last_alert_time(tmp_db, "backup")
    assert result is not None
    assert result == when


def test_last_alert_returns_most_recent(tmp_db):
    record_alert(tmp_db, "backup", when=_dt(0))
    record_alert(tmp_db, "backup", when=_dt(10))
    record_alert(tmp_db, "backup", when=_dt(5))
    result = last_alert_time(tmp_db, "backup")
    assert result == _dt(10)


def test_last_alert_isolated_by_job(tmp_db):
    record_alert(tmp_db, "backup", when=_dt(0))
    assert last_alert_time(tmp_db, "cleanup") is None


def test_should_alert_when_no_previous(tmp_db):
    assert should_alert(tmp_db, "backup", cooldown_minutes=30) is True


def test_should_alert_false_within_cooldown(tmp_db):
    fixed_now = _dt(0)
    record_alert(tmp_db, "backup", when=fixed_now)
    # 10 minutes later — within 30-minute cooldown
    with patch("cronwatcher.notifier._utcnow", return_value=_dt(10)):
        assert should_alert(tmp_db, "backup", cooldown_minutes=30) is False


def test_should_alert_true_after_cooldown(tmp_db):
    fixed_now = _dt(0)
    record_alert(tmp_db, "backup", when=fixed_now)
    # 31 minutes later — past the 30-minute cooldown
    with patch("cronwatcher.notifier._utcnow", return_value=_dt(31)):
        assert should_alert(tmp_db, "backup", cooldown_minutes=30) is True


def test_should_alert_zero_cooldown_always_true(tmp_db):
    record_alert(tmp_db, "backup", when=_dt(0))
    with patch("cronwatcher.notifier._utcnow", return_value=_dt(0)):
        assert should_alert(tmp_db, "backup", cooldown_minutes=0) is True
