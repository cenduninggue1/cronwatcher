"""Heartbeat tracking: record periodic pings from cron jobs and detect missed ones."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from cronwatcher.db import get_connection


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_table(db_path: str) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS heartbeats (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                job_name  TEXT NOT NULL,
                pinged_at TEXT NOT NULL
            )
            """
        )


def record_heartbeat(db_path: str, job_name: str) -> int:
    """Record a heartbeat ping for *job_name*. Returns the new row id."""
    _ensure_table(db_path)
    now = _utcnow().isoformat()
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO heartbeats (job_name, pinged_at) VALUES (?, ?)",
            (job_name, now),
        )
        return cur.lastrowid  # type: ignore[return-value]


def last_heartbeat(db_path: str, job_name: str) -> Optional[datetime]:
    """Return the most recent heartbeat time for *job_name*, or ``None``."""
    _ensure_table(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT pinged_at FROM heartbeats WHERE job_name = ? ORDER BY pinged_at DESC LIMIT 1",
            (job_name,),
        ).fetchone()
    if row is None:
        return None
    return datetime.fromisoformat(row[0])


def is_overdue(db_path: str, job_name: str, max_seconds: int) -> bool:
    """Return ``True`` when the last heartbeat is older than *max_seconds* (or absent)."""
    last = last_heartbeat(db_path, job_name)
    if last is None:
        return True
    last_utc = last if last.tzinfo else last.replace(tzinfo=timezone.utc)
    elapsed = (_utcnow() - last_utc).total_seconds()
    return elapsed > max_seconds


def prune_heartbeats(db_path: str, job_name: str, keep: int = 100) -> int:
    """Delete old heartbeat rows for *job_name*, keeping only the *keep* most recent.

    Returns the number of rows deleted.
    """
    _ensure_table(db_path)
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            DELETE FROM heartbeats
            WHERE job_name = ?
              AND id NOT IN (
                  SELECT id FROM heartbeats
                  WHERE job_name = ?
                  ORDER BY pinged_at DESC
                  LIMIT ?
              )
            """,
            (job_name, job_name, keep),
        )
        return cur.rowcount
