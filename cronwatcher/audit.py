"""Audit log: records significant daemon events (start, stop, config reload, etc.)."""

from __future__ import annotations

import datetime
from typing import List, Optional

from cronwatcher.db import get_connection


def _utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow()


def _ensure_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        TEXT    NOT NULL,
            event     TEXT    NOT NULL,
            detail    TEXT
        )
        """
    )
    conn.commit()


def record_event(db_path: str, event: str, detail: Optional[str] = None) -> int:
    """Insert an audit event and return its row id."""
    conn = get_connection(db_path)
    _ensure_table(conn)
    ts = _utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    cur = conn.execute(
        "INSERT INTO audit_log (ts, event, detail) VALUES (?, ?, ?)",
        (ts, event, detail),
    )
    conn.commit()
    return cur.lastrowid


def get_recent_events(
    db_path: str, limit: int = 50
) -> List[dict]:
    """Return the *limit* most recent audit events, newest first."""
    conn = get_connection(db_path)
    _ensure_table(conn)
    rows = conn.execute(
        "SELECT id, ts, event, detail FROM audit_log ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [
        {"id": r[0], "ts": r[1], "event": r[2], "detail": r[3]}
        for r in rows
    ]


def format_events(events: List[dict]) -> str:
    """Return a human-readable string of audit events."""
    if not events:
        return "No audit events recorded."
    lines = []
    for e in events:
        detail_part = f"  {e['detail']}" if e["detail"] else ""
        lines.append(f"{e['ts']}  [{e['event']}]{detail_part}")
    return "\n".join(lines)
