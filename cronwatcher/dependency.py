"""Job dependency checking — ensures a job only runs if its dependencies succeeded recently."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from cronwatcher.db import get_connection


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DependencyResult:
    job_name: str
    satisfied: bool
    last_success: Optional[datetime]
    reason: str


def get_last_success(db_path: str, job_name: str) -> Optional[datetime]:
    """Return the timestamp of the most recent successful run for *job_name*, or None."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT finished_at
            FROM runs
            WHERE job_name = ? AND exit_code = 0 AND finished_at IS NOT NULL
            ORDER BY finished_at DESC
            LIMIT 1
            """,
            (job_name,),
        ).fetchone()
    if row is None:
        return None
    return datetime.fromisoformat(row["finished_at"]).replace(tzinfo=timezone.utc)


def check_dependency(
    db_path: str,
    dep_name: str,
    max_age_seconds: Optional[int] = None,
) -> DependencyResult:
    """Check whether *dep_name* has a recent enough successful run.

    If *max_age_seconds* is None, any past success is acceptable.
    """
    last = get_last_success(db_path, dep_name)
    if last is None:
        return DependencyResult(
            job_name=dep_name,
            satisfied=False,
            last_success=None,
            reason=f"dependency '{dep_name}' has never succeeded",
        )

    if max_age_seconds is not None:
        age = (_utcnow() - last).total_seconds()
        if age > max_age_seconds:
            return DependencyResult(
                job_name=dep_name,
                satisfied=False,
                last_success=last,
                reason=(
                    f"dependency '{dep_name}' last succeeded {age:.0f}s ago "
                    f"(limit {max_age_seconds}s)"
                ),
            )

    return DependencyResult(
        job_name=dep_name,
        satisfied=True,
        last_success=last,
        reason="ok",
    )


def all_dependencies_satisfied(
    db_path: str,
    dependencies: List[str],
    max_age_seconds: Optional[int] = None,
) -> tuple[bool, List[DependencyResult]]:
    """Return (all_ok, results) for every dependency in *dependencies*."""
    results = [
        check_dependency(db_path, dep, max_age_seconds) for dep in dependencies
    ]
    return all(r.satisfied for r in results), results
