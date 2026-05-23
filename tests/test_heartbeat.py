"""Tests for cronwatcher.heartbeat."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from cronwatcher.heartbeat import (
    is_overdue,
    last_heartbeat,
    prune_heartbeats,
    record_heartbeat,
)


@pytest.fixture()
def tmp_db(tmp_path):
    return str(tmp_path / "test.db")


def _dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# record_heartbeat / last_heartbeat
# ---------------------------------------------------------------------------

def test_last_heartbeat_none_when_empty(tmp_db):
    assert last_heartbeat(tmp_db, "backup") is None


def test_record_returns_positive_id(tmp_db):
    row_id = record_heartbeat(tmp_db, "backup")
    assert isinstance(row_id, int)
    assert row_id > 0


def test_last_heartbeat_returns_most_recent(tmp_db):
    early = _dt("2024-01-01T00:00:00")
    late = _dt("2024-06-01T12:00:00")

    with patch("cronwatcher.heartbeat._utcnow", return_value=early):
        record_heartbeat(tmp_db, "backup")
    with patch("cronwatcher.heartbeat._utcnow", return_value=late):
        record_heartbeat(tmp_db, "backup")

    result = last_heartbeat(tmp_db, "backup")
    assert result is not None
    result_utc = result if result.tzinfo else result.replace(tzinfo=timezone.utc)
    assert result_utc == late


def test_last_heartbeat_isolated_by_job_name(tmp_db):
    record_heartbeat(tmp_db, "job_a")
    assert last_heartbeat(tmp_db, "job_b") is None


# ---------------------------------------------------------------------------
# is_overdue
# ---------------------------------------------------------------------------

def test_is_overdue_true_when_no_heartbeat(tmp_db):
    assert is_overdue(tmp_db, "nightly", max_seconds=3600) is True


def test_is_overdue_false_when_recent(tmp_db):
    now = datetime.now(timezone.utc)
    with patch("cronwatcher.heartbeat._utcnow", return_value=now):
        record_heartbeat(tmp_db, "nightly")
    # Still the same "now" when checking
    with patch("cronwatcher.heartbeat._utcnow", return_value=now):
        assert is_overdue(tmp_db, "nightly", max_seconds=3600) is False


def test_is_overdue_true_when_stale(tmp_db):
    old = _dt("2024-01-01T00:00:00")
    with patch("cronwatcher.heartbeat._utcnow", return_value=old):
        record_heartbeat(tmp_db, "nightly")
    # Check with current real time — always > 1 s after 2024-01-01
    assert is_overdue(tmp_db, "nightly", max_seconds=1) is True


# ---------------------------------------------------------------------------
# prune_heartbeats
# ---------------------------------------------------------------------------

def test_prune_removes_old_rows(tmp_db):
    for _ in range(10):
        record_heartbeat(tmp_db, "frequent")

    deleted = prune_heartbeats(tmp_db, "frequent", keep=3)
    assert deleted == 7


def test_prune_keeps_most_recent(tmp_db):
    for _ in range(5):
        record_heartbeat(tmp_db, "frequent")

    prune_heartbeats(tmp_db, "frequent", keep=2)
    # After pruning only 2 rows remain; another prune deletes nothing
    assert prune_heartbeats(tmp_db, "frequent", keep=2) == 0
