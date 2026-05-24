"""Environment pre-flight checks for cronwatcher.

Verifies that required executables, environment variables, and paths
exist before a job is executed, logging warnings for any issues found.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from typing import List

from cronwatcher.config import JobConfig
from cronwatcher.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass
class CheckResult:
    job_name: str
    missing_vars: List[str] = field(default_factory=list)
    missing_executables: List[str] = field(default_factory=list)
    missing_paths: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.missing_vars or self.missing_executables or self.missing_paths)

    def __str__(self) -> str:
        lines = [f"EnvCheck for '{self.job_name}':"]
        if self.missing_vars:
            lines.append(f"  missing env vars : {', '.join(self.missing_vars)}")
        if self.missing_executables:
            lines.append(f"  missing executables: {', '.join(self.missing_executables)}")
        if self.missing_paths:
            lines.append(f"  missing paths    : {', '.join(self.missing_paths)}")
        if self.ok:
            lines.append("  all checks passed")
        return "\n".join(lines)


def check_job_environment(job: JobConfig) -> CheckResult:
    """Run all environment checks for *job* and return a CheckResult."""
    result = CheckResult(job_name=job.name)

    for var in getattr(job, "required_env", []) or []:
        if not os.environ.get(var):
            result.missing_vars.append(var)
            logger.warning("job '%s': required env var '%s' is not set", job.name, var)

    for exe in getattr(job, "required_executables", []) or []:
        if shutil.which(exe) is None:
            result.missing_executables.append(exe)
            logger.warning("job '%s': executable '%s' not found on PATH", job.name, exe)

    for path in getattr(job, "required_paths", []) or []:
        if not os.path.exists(path):
            result.missing_paths.append(path)
            logger.warning("job '%s': required path '%s' does not exist", job.name, path)

    return result


def check_all_jobs(jobs: List[JobConfig]) -> List[CheckResult]:
    """Run environment checks for every job; return results for all jobs."""
    return [check_job_environment(job) for job in jobs]
