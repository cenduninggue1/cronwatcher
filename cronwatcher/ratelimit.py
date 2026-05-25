"""Per-job alert rate limiting backed by the SQLite database.

Provides a sliding-window counter so that a noisy failing job cannot
flood an on-call inbox: only *max_alerts* notifications are emitted
within any rolling *window_seconds* period.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS alert_rate_limit (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name      TEXT    NOT NULL,
            alerted_at    TEXT    NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_arl_job_time "
        "ON alert_rate_limit (job_name, alerted_at)"
    )
    conn.commit()


def count_recent_alerts(
    conn: sqlite3.Connection,
    job_name: str,
    window_seconds: int,
) -> int:
    """Return the number of alerts recorded for *job_name* within the window."""
    _ensure_table(conn)
    cutoff = _utcnow().timestamp() - window_seconds
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
    row = conn.execute(
        "SELECT COUNT(*) FROM alert_rate_limit "
        "WHERE job_name = ? AND alerted_at >= ?",
        (job_name, cutoff_iso),
    ).fetchone()
    return int(row[0])


def record_rate_limit_alert(
    conn: sqlite3.Connection,
    job_name: str,
    *,
    now: Optional[datetime] = None,
) -> int:
    """Persist a new alert timestamp and return its row id."""
    _ensure_table(conn)
    ts = (now or _utcnow()).isoformat()
    cur = conn.execute(
        "INSERT INTO alert_rate_limit (job_name, alerted_at) VALUES (?, ?)",
        (job_name, ts),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def is_rate_limited(
    conn: sqlite3.Connection,
    job_name: str,
    window_seconds: int,
    max_alerts: int,
) -> bool:
    """Return True when *job_name* has exhausted its alert quota.

    A *window_seconds* of 0 or a *max_alerts* of 0 disables limiting.
    """
    if window_seconds <= 0 or max_alerts <= 0:
        return False
    return count_recent_alerts(conn, job_name, window_seconds) >= max_alerts


def prune_old_entries(
    conn: sqlite3.Connection,
    window_seconds: int,
) -> int:
    """Delete entries older than *window_seconds*. Returns rows removed."""
    _ensure_table(conn)
    cutoff = _utcnow().timestamp() - window_seconds
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
    cur = conn.execute(
        "DELETE FROM alert_rate_limit WHERE alerted_at < ?",
        (cutoff_iso,),
    )
    conn.commit()
    return cur.rowcount
