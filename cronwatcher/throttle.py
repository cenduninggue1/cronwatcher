"""Alert throttling: prevent repeated alerts for the same job within a cooldown window."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from cronwatcher.db import get_connection
from cronwatcher.notifier import _ensure_table, last_alert_time, record_alert


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def is_throttled(db_path: str, job_name: str, cooldown_minutes: int) -> bool:
    """Return True if an alert for *job_name* was sent within *cooldown_minutes*."""
    if cooldown_minutes <= 0:
        return False
    conn = get_connection(db_path)
    _ensure_table(conn)
    last = last_alert_time(conn, job_name)
    if last is None:
        return False
    elapsed = (_utcnow() - last).total_seconds() / 60.0
    return elapsed < cooldown_minutes


def maybe_record_alert(
    db_path: str,
    job_name: str,
    cooldown_minutes: int,
) -> bool:
    """Record an alert for *job_name* and return True, unless throttled.

    Returns False (and does NOT record) when the job is still within its
    cooldown window.
    """
    if is_throttled(db_path, job_name, cooldown_minutes):
        return False
    conn = get_connection(db_path)
    _ensure_table(conn)
    record_alert(conn, job_name)
    return True


def reset_throttle(db_path: str, job_name: str) -> int:
    """Delete all alert records for *job_name*.  Returns number of rows removed."""
    conn = get_connection(db_path)
    _ensure_table(conn)
    cur = conn.execute(
        "DELETE FROM alert_log WHERE job_name = ?", (job_name,)
    )
    conn.commit()
    return cur.rowcount
