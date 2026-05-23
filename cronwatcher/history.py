"""Query and summarize cron job execution history from the database."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from cronwatcher.db import get_connection


@dataclass
class JobRun:
    run_id: int
    job_name: str
    started_at: datetime
    finished_at: Optional[datetime]
    exit_code: Optional[int]
    stderr: Optional[str]

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()


def _row_to_job_run(row: tuple) -> JobRun:
    run_id, job_name, started_at, finished_at, exit_code, stderr = row
    return JobRun(
        run_id=run_id,
        job_name=job_name,
        started_at=datetime.fromisoformat(started_at).replace(tzinfo=timezone.utc),
        finished_at=(
            datetime.fromisoformat(finished_at).replace(tzinfo=timezone.utc)
            if finished_at
            else None
        ),
        exit_code=exit_code,
        stderr=stderr,
    )


def get_recent_runs(db_path: str, job_name: str, limit: int = 20) -> List[JobRun]:
    """Return the most recent runs for a given job, newest first."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, job_name, started_at, finished_at, exit_code, stderr
            FROM runs
            WHERE job_name = ?
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (job_name, limit),
        ).fetchall()
    return [_row_to_job_run(r) for r in rows]


def get_failed_runs(db_path: str, limit: int = 50) -> List[JobRun]:
    """Return recent failed runs across all jobs."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, job_name, started_at, finished_at, exit_code, stderr
            FROM runs
            WHERE exit_code IS NOT NULL AND exit_code != 0
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_row_to_job_run(r) for r in rows]


def get_last_run(db_path: str, job_name: str) -> Optional[JobRun]:
    """Return the single most recent run for a job, or None."""
    runs = get_recent_runs(db_path, job_name, limit=1)
    return runs[0] if runs else None
