"""Generate a summary report of recent cron job activity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from cronwatcher.history import JobRun, get_recent_runs, get_last_run
from cronwatcher.db import get_connection


@dataclass
class JobSummary:
    job_name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    last_run_at: str | None
    last_exit_code: int | None

    @property
    def failure_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.failed_runs / self.total_runs

    @property
    def success_rate(self) -> float:
        return 1.0 - self.failure_rate


def summarise_job(db_path: str, job_name: str, limit: int = 50) -> JobSummary:
    """Return a summary of recent runs for a single job."""
    runs: List[JobRun] = get_recent_runs(db_path, job_name, limit=limit)
    last: JobRun | None = get_last_run(db_path, job_name)

    total = len(runs)
    successful = sum(1 for r in runs if r.exit_code == 0)
    failed = total - successful

    return JobSummary(
        job_name=job_name,
        total_runs=total,
        successful_runs=successful,
        failed_runs=failed,
        last_run_at=last.started_at if last else None,
        last_exit_code=last.exit_code if last else None,
    )


def summarise_all_jobs(db_path: str, limit: int = 50) -> List[JobSummary]:
    """Return summaries for every job that has recorded runs."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT DISTINCT job_name FROM runs ORDER BY job_name"
        ).fetchall()
    finally:
        conn.close()

    return [summarise_job(db_path, row["job_name"], limit=limit) for row in rows]


def format_summary_table(summaries: List[JobSummary]) -> str:
    """Render a plain-text table of job summaries."""
    if not summaries:
        return "No job runs recorded."

    header = f"{'Job':<30} {'Runs':>6} {'OK':>6} {'FAIL':>6} {'Fail%':>7}  Last Run"
    separator = "-" * len(header)
    lines = [header, separator]

    for s in summaries:
        pct = f"{s.failure_rate * 100:.1f}%"
        last = s.last_run_at or "never"
        lines.append(
            f"{s.job_name:<30} {s.total_runs:>6} {s.successful_runs:>6} "
            f"{s.failed_runs:>6} {pct:>7}  {last}"
        )

    return "\n".join(lines)
