"""Tag-based filtering and grouping for cron jobs."""

from __future__ import annotations

from typing import Iterable

from cronwatcher.config import JobConfig


def get_jobs_by_tag(jobs: Iterable[JobConfig], tag: str) -> list[JobConfig]:
    """Return all jobs that carry the given tag."""
    return [j for j in jobs if tag in (j.tags or [])]


def get_all_tags(jobs: Iterable[JobConfig]) -> list[str]:
    """Return a sorted, deduplicated list of every tag used across all jobs."""
    seen: set[str] = set()
    for job in jobs:
        for t in job.tags or []:
            seen.add(t)
    return sorted(seen)


def group_by_tag(jobs: Iterable[JobConfig]) -> dict[str, list[JobConfig]]:
    """Return a mapping of tag -> list of jobs that carry that tag.

    A job appears under every tag it carries.
    Jobs with no tags appear under the special key ``"(untagged)"``.
    """
    result: dict[str, list[JobConfig]] = {}
    for job in jobs:
        if not job.tags:
            result.setdefault("(untagged)", []).append(job)
        else:
            for t in job.tags:
                result.setdefault(t, []).append(job)
    return result


def format_tag_summary(groups: dict[str, list[JobConfig]]) -> str:
    """Render a human-readable summary of jobs grouped by tag."""
    if not groups:
        return "No jobs found."
    lines: list[str] = []
    for tag in sorted(groups):
        job_names = ", ".join(j.name for j in groups[tag])
        lines.append(f"[{tag}] {job_names}")
    return "\n".join(lines)
