"""Daemon status reporting: checks heartbeat freshness and summarises overall health."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from cronwatcher.heartbeat import last_heartbeat, is_overdue
from cronwatcher.summary import summarise_all_jobs
from cronwatcher.db import get_connection


@dataclass
class DaemonStatus:
    running: bool
    last_heartbeat: Optional[datetime]
    heartbeat_overdue: bool
    total_jobs: int
    jobs_with_failures: int

    @property
    def healthy(self) -> bool:
        return self.running and not self.heartbeat_overdue and self.jobs_with_failures == 0


def get_daemon_status(db_path: str, overdue_seconds: int = 120) -> DaemonStatus:
    """Return a snapshot of the current daemon health."""
    conn = get_connection(db_path)

    hb = last_heartbeat(conn)
    overdue = is_overdue(conn, overdue_seconds)
    running = hb is not None and not overdue

    summaries = summarise_all_jobs(conn)
    total = len(summaries)
    with_failures = sum(1 for s in summaries if s.failure_count > 0)

    conn.close()

    return DaemonStatus(
        running=running,
        last_heartbeat=hb,
        heartbeat_overdue=overdue,
        total_jobs=total,
        jobs_with_failures=with_failures,
    )


def format_status(status: DaemonStatus) -> str:
    """Render a DaemonStatus as a human-readable string."""
    lines = []
    health = "OK" if status.healthy else "DEGRADED"
    lines.append(f"Status : {health}")
    lines.append(f"Running: {'yes' if status.running else 'no'}")

    if status.last_heartbeat:
        ts = status.last_heartbeat.strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        ts = "never"
    lines.append(f"Last heartbeat : {ts}")
    lines.append(f"Heartbeat overdue: {'yes' if status.heartbeat_overdue else 'no'}")
    lines.append(f"Tracked jobs   : {status.total_jobs}")
    lines.append(f"Jobs w/ failures: {status.jobs_with_failures}")
    return "\n".join(lines)
