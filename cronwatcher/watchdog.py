"""Watchdog: detects jobs that started but never finished (hung/killed)."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import List

from cronwatcher.db import get_connection


def _utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow()


@dataclass
class HungJob:
    run_id: int
    job_name: str
    started_at: datetime.datetime
    running_seconds: float


def find_hung_jobs(
    db_path: str,
    timeout_seconds: int = 3600,
    reference_time: datetime.datetime | None = None,
) -> List[HungJob]:
    """Return runs that started but have no finish record and exceed *timeout_seconds*."""
    now = reference_time or _utcnow()
    cutoff = now - datetime.timedelta(seconds=timeout_seconds)

    con = get_connection(db_path)
    rows = con.execute(
        """
        SELECT id, job_name, started_at
        FROM runs
        WHERE finished_at IS NULL
          AND started_at <= ?
        ORDER BY started_at
        """,
        (cutoff.isoformat(),),
    ).fetchall()
    con.close()

    hung: List[HungJob] = []
    for row in rows:
        started = datetime.datetime.fromisoformat(row["started_at"])
        delta = (now - started).total_seconds()
        hung.append(HungJob(run_id=row["id"], job_name=row["job_name"],
                            started_at=started, running_seconds=delta))
    return hung


def mark_hung_jobs(
    db_path: str,
    timeout_seconds: int = 3600,
    reference_time: datetime.datetime | None = None,
) -> List[HungJob]:
    """Mark hung runs as failed with exit_code=-1 and return the affected list."""
    hung = find_hung_jobs(db_path, timeout_seconds, reference_time)
    if not hung:
        return hung

    now = reference_time or _utcnow()
    con = get_connection(db_path)
    for job in hung:
        con.execute(
            """
            UPDATE runs
            SET finished_at = ?, exit_code = -1, stderr = 'terminated by watchdog'
            WHERE id = ?
            """,
            (now.isoformat(), job.run_id),
        )
    con.commit()
    con.close()
    return hung
