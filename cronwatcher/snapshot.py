"""Point-in-time snapshot of all job statuses for reporting and diagnostics."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import List, Optional

from cronwatcher.config import Config, JobConfig
from cronwatcher.history import get_last_run, JobRun
from cronwatcher.stale import find_stale_jobs, StaleJob
from cronwatcher.watchdog import find_hung_jobs, HungJob


@dataclass
class JobSnapshot:
    job_name: str
    schedule: str
    last_run: Optional[JobRun]
    is_stale: bool
    is_hung: bool
    stale_info: Optional[StaleJob] = None
    hung_info: Optional[HungJob] = None


def _utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow()


def build_snapshot(config: Config, db_path: str) -> List[JobSnapshot]:
    """Build a snapshot of all jobs at the current moment."""
    stale_jobs = {s.job_name: s for s in find_stale_jobs(config, db_path)}
    hung_jobs = {h.job_name: h for h in find_hung_jobs(db_path)}

    snapshots: List[JobSnapshot] = []
    for job in config.jobs:
        last_run = get_last_run(db_path, job.name)
        stale_info = stale_jobs.get(job.name)
        hung_info = hung_jobs.get(job.name)
        snapshots.append(
            JobSnapshot(
                job_name=job.name,
                schedule=job.schedule,
                last_run=last_run,
                is_stale=stale_info is not None,
                is_hung=hung_info is not None,
                stale_info=stale_info,
                hung_info=hung_info,
            )
        )
    return snapshots


def format_snapshot(snapshots: List[JobSnapshot]) -> str:
    """Render a human-readable table of job snapshots."""
    if not snapshots:
        return "No jobs configured."

    lines = [f"{'JOB':<30} {'SCHEDULE':<20} {'LAST RUN':<22} {'STATUS'}",
             "-" * 80]
    for s in snapshots:
        last = s.last_run.started_at.strftime("%Y-%m-%d %H:%M:%S") if s.last_run else "never"
        flags = []
        if s.is_hung:
            flags.append("HUNG")
        if s.is_stale:
            flags.append("STALE")
        if not flags and s.last_run is not None:
            from cronwatcher.history import succeeded
            flags.append("OK" if succeeded(s.last_run) else "FAILED")
        status = ", ".join(flags) if flags else "PENDING"
        lines.append(f"{s.job_name:<30} {s.schedule:<20} {last:<22} {status}")
    return "\n".join(lines)
