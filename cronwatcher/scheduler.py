"""Scheduler: reads Config, determines which jobs are due, and runs them."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

from croniter import croniter

from cronwatcher.config import Config, JobConfig
from cronwatcher.db import get_connection, init_db
from cronwatcher.runner import run_job

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def jobs_due(jobs: List[JobConfig], now: datetime | None = None) -> List[JobConfig]:
    """Return jobs whose cron schedule matches the current minute."""
    if now is None:
        now = _utcnow()
    # croniter checks whether 'now' falls on a scheduled tick by looking
    # one period back; we consider a job due when the previous scheduled
    # time is within the same minute as *now*.
    due = []
    for job in jobs:
        try:
            cron = croniter(job.schedule, now)
            prev: datetime = cron.get_prev(datetime)
            delta = (now - prev).total_seconds()
            if 0 <= delta < 60:
                due.append(job)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Invalid schedule for job '%s': %s", job.name, exc)
    return due


def run_due_jobs(config: Config) -> None:
    """Initialise DB, find due jobs, and execute each one."""
    db_path = config.database
    init_db(db_path)
    conn = get_connection(db_path)
    now = _utcnow()
    due = jobs_due(config.jobs, now)
    if not due:
        logger.debug("No jobs due at %s", now.isoformat())
        return
    for job in due:
        logger.info("Running due job: %s", job.name)
        run_job(job, conn, config.alert)
    conn.close()
