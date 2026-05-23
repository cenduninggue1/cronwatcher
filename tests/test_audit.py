"""Tests for cronwatcher.audit."""

from __future__ import annotations

import os
import pytest

from cronwatcher.db import init_db
from cronwatcher.audit import (
    record_event,
    get_recent_events,
    format_events,
)


@pytest.fixture()
def tmp_db(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def test_record_event_returns_positive_id(tmp_db):
    row_id = record_event(tmp_db, "daemon_start")
    assert row_id >= 1


def test_record_event_increments_id(tmp_db):
    id1 = record_event(tmp_db, "daemon_start")
    id2 = record_event(tmp_db, "daemon_stop")
    assert id2 > id1


def test_get_recent_events_empty(tmp_db):
    events = get_recent_events(tmp_db)
    assert events == []


def test_get_recent_events_returns_inserted(tmp_db):
    record_event(tmp_db, "daemon_start", detail="pid=1234")
    events = get_recent_events(tmp_db)
    assert len(events) == 1
    assert events[0]["event"] == "daemon_start"
    assert events[0]["detail"] == "pid=1234"


def test_get_recent_events_newest_first(tmp_db):
    record_event(tmp_db, "daemon_start")
    record_event(tmp_db, "config_reload")
    record_event(tmp_db, "daemon_stop")
    events = get_recent_events(tmp_db)
    assert events[0]["event"] == "daemon_stop"
    assert events[-1]["event"] == "daemon_start"


def test_get_recent_events_respects_limit(tmp_db):
    for i in range(10):
        record_event(tmp_db, "tick", detail=str(i))
    events = get_recent_events(tmp_db, limit=3)
    assert len(events) == 3


def test_format_events_empty():
    result = format_events([])
    assert "No audit" in result


def test_format_events_contains_event_name(tmp_db):
    record_event(tmp_db, "daemon_start", detail="pid=99")
    events = get_recent_events(tmp_db)
    output = format_events(events)
    assert "daemon_start" in output
    assert "pid=99" in output


def test_format_events_no_detail(tmp_db):
    record_event(tmp_db, "daemon_stop")
    events = get_recent_events(tmp_db)
    output = format_events(events)
    assert "daemon_stop" in output
    # No extra whitespace / crash when detail is None
    assert "None" not in output
