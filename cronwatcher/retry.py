"""Retry policy evaluation for cron jobs."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from cronwatcher.config import JobConfig


@dataclass
class RetryState:
    """Tracks retry attempts for a single job execution."""

    job_name: str
    max_attempts: int
    delay_seconds: float
    attempt: int = 0
    last_exit_code: Optional[int] = None
    exhausted: bool = False


def should_retry(state: RetryState, exit_code: int) -> bool:
    """Return True if the job should be retried given the current state."""
    if exit_code == 0:
        return False
    state.last_exit_code = exit_code
    state.attempt += 1
    if state.attempt >= state.max_attempts:
        state.exhausted = True
        return False
    return True


def make_retry_state(job: JobConfig) -> RetryState:
    """Build a RetryState from a JobConfig.

    Falls back to sensible defaults when retry fields are absent.
    """
    max_attempts: int = getattr(job, "retry_attempts", 1) or 1
    delay: float = getattr(job, "retry_delay_seconds", 0.0) or 0.0
    return RetryState(
        job_name=job.name,
        max_attempts=max_attempts,
        delay_seconds=delay,
    )


def wait_before_retry(state: RetryState, _sleep=time.sleep) -> None:
    """Sleep for the configured delay before the next retry attempt."""
    if state.delay_seconds > 0:
        _sleep(state.delay_seconds)


def run_with_retry(job: JobConfig, runner_fn, _sleep=time.sleep):
    """Execute *runner_fn(job)* with retry logic.

    *runner_fn* must return a result object with an ``exit_code`` attribute
    (compatible with the dict returned by ``cronwatcher.runner.run_job``).

    Returns the last result produced and the RetryState so callers can
    inspect how many attempts were made.
    """
    state = make_retry_state(job)
    result = None
    while True:
        result = runner_fn(job)
        exit_code = result.get("exit_code", 0) if isinstance(result, dict) else result.exit_code
        if not should_retry(state, exit_code):
            break
        wait_before_retry(state, _sleep=_sleep)
    return result, state
