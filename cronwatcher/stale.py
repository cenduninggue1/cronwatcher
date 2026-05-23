"""Detect jobs that have not run recently (stale jobs)."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import List, Optional

from cronwatcher.db import get_connection
from cronwatcher.config import JobConfig


def _utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow()


@dataclass
class StaleJob:
    job_name: str
    last_run_at: Optional[datetime.datetime]
    expected_interval_minutes: int
    minutes_overdue: float


def get_last_run_time(db_path: str, job_name: str) -> Optional[datetime.datetime]:
    """Return the UTC started_at time of the most recent run for a job."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT started_at FROM runs
            WHERE job_name = ?
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (job_name,),
        ).fetchone()
    if row is None:
        return None
    return datetime.datetime.fromisoformat(row["started_at"])


def find_stale_jobs(
    db_path: str,
    jobs: List[JobConfig],
    now: Optional[datetime.datetime] = None,
) -> List[StaleJob]:
    """Return jobs whose last run is older than their expected interval.

    A job is considered stale when:
      - it has never run, OR
      - its last run started more than ``stale_after_minutes`` minutes ago.

    Only jobs with ``stale_after_minutes`` configured are checked.
    """
    if now is None:
        now = _utcnow()

    stale: List[StaleJob] = []
    for job in jobs:
        threshold = getattr(job, "stale_after_minutes", None)
        if threshold is None:
            continue

        last_run = get_last_run_time(db_path, job.name)
        if last_run is None:
            minutes_overdue = float(threshold)
        else:
            age_minutes = (now - last_run).total_seconds() / 60.0
            if age_minutes <= threshold:
                continue
            minutes_overdue = age_minutes - threshold

        stale.append(
            StaleJob(
                job_name=job.name,
                last_run_at=last_run,
                expected_interval_minutes=threshold,
                minutes_overdue=round(minutes_overdue, 2),
            )
        )
    return stale
