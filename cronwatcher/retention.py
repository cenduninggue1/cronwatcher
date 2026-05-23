"""Retention policy: prune old job run records from the database."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from cronwatcher.db import get_connection

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def prune_runs(
    db_path: str,
    max_age_days: Optional[int] = None,
    max_rows_per_job: Optional[int] = None,
) -> int:
    """Delete old runs according to retention policy.

    Args:
        db_path: Path to the SQLite database file.
        max_age_days: Remove runs older than this many days. ``None`` skips.
        max_rows_per_job: Keep only the most recent N runs per job name.
            ``None`` skips.

    Returns:
        Total number of rows deleted.
    """
    deleted = 0

    with get_connection(db_path) as conn:
        if max_age_days is not None:
            cutoff = _utcnow() - timedelta(days=max_age_days)
            cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%S")
            cur = conn.execute(
                "DELETE FROM job_runs WHERE started_at < ?",
                (cutoff_str,),
            )
            deleted += cur.rowcount
            logger.debug(
                "Pruned %d run(s) older than %s days (cutoff %s)",
                cur.rowcount,
                max_age_days,
                cutoff_str,
            )

        if max_rows_per_job is not None:
            job_names = [
                row[0]
                for row in conn.execute(
                    "SELECT DISTINCT job_name FROM job_runs"
                ).fetchall()
            ]
            for job_name in job_names:
                cur = conn.execute(
                    """
                    DELETE FROM job_runs
                    WHERE job_name = ?
                      AND id NOT IN (
                          SELECT id FROM job_runs
                          WHERE job_name = ?
                          ORDER BY started_at DESC
                          LIMIT ?
                      )
                    """,
                    (job_name, job_name, max_rows_per_job),
                )
                deleted += cur.rowcount
                if cur.rowcount:
                    logger.debug(
                        "Pruned %d run(s) for job '%s' (kept last %d)",
                        cur.rowcount,
                        job_name,
                        max_rows_per_job,
                    )

    logger.info("Retention pruning complete — %d row(s) deleted.", deleted)
    return deleted
