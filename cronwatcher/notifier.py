"""Throttled alert notifier — suppresses repeated alerts for the same job."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from cronwatcher.db import get_connection


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS alert_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name  TEXT    NOT NULL,
            alerted_at TEXT   NOT NULL
        )
        """
    )
    conn.commit()


def last_alert_time(db_path: str, job_name: str) -> Optional[datetime]:
    """Return the UTC datetime of the most recent alert for *job_name*, or None."""
    with get_connection(db_path) as conn:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT alerted_at FROM alert_log WHERE job_name = ? ORDER BY alerted_at DESC LIMIT 1",
            (job_name,),
        ).fetchone()
    if row is None:
        return None
    return datetime.fromisoformat(row[0])


def record_alert(db_path: str, job_name: str, when: Optional[datetime] = None) -> None:
    """Persist an alert event for *job_name*."""
    ts = (when or _utcnow()).isoformat()
    with get_connection(db_path) as conn:
        _ensure_table(conn)
        conn.execute(
            "INSERT INTO alert_log (job_name, alerted_at) VALUES (?, ?)",
            (job_name, ts),
        )
        conn.commit()


def should_alert(db_path: str, job_name: str, cooldown_minutes: int) -> bool:
    """Return True when enough time has passed since the last alert (or none exists)."""
    if cooldown_minutes <= 0:
        return True
    last = last_alert_time(db_path, job_name)
    if last is None:
        return True
    elapsed = (_utcnow() - last).total_seconds() / 60
    return elapsed >= cooldown_minutes
