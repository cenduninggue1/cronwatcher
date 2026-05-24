"""Tests for cronwatcher.retry."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from cronwatcher.retry import (
    RetryState,
    make_retry_state,
    run_with_retry,
    should_retry,
    wait_before_retry,
)


def _job(name="backup", retry_attempts=3, retry_delay_seconds=0.0):
    job = MagicMock()
    job.name = name
    job.retry_attempts = retry_attempts
    job.retry_delay_seconds = retry_delay_seconds
    return job


# ---------------------------------------------------------------------------
# should_retry
# ---------------------------------------------------------------------------

def test_should_retry_returns_false_on_success():
    state = RetryState(job_name="x", max_attempts=3, delay_seconds=0)
    assert should_retry(state, 0) is False


def test_should_retry_returns_true_when_attempts_remain():
    state = RetryState(job_name="x", max_attempts=3, delay_seconds=0)
    assert should_retry(state, 1) is True
    assert state.attempt == 1
    assert not state.exhausted


def test_should_retry_exhausted_after_max_attempts():
    state = RetryState(job_name="x", max_attempts=2, delay_seconds=0)
    should_retry(state, 1)  # attempt 1 -> still retryable
    result = should_retry(state, 1)  # attempt 2 -> exhausted
    assert result is False
    assert state.exhausted is True


# ---------------------------------------------------------------------------
# make_retry_state
# ---------------------------------------------------------------------------

def test_make_retry_state_uses_job_fields():
    job = _job(retry_attempts=5, retry_delay_seconds=2.5)
    state = make_retry_state(job)
    assert state.max_attempts == 5
    assert state.delay_seconds == 2.5
    assert state.job_name == "backup"


def test_make_retry_state_defaults_to_one_attempt():
    job = _job(retry_attempts=None, retry_delay_seconds=None)
    state = make_retry_state(job)
    assert state.max_attempts == 1
    assert state.delay_seconds == 0.0


# ---------------------------------------------------------------------------
# wait_before_retry
# ---------------------------------------------------------------------------

def test_wait_before_retry_sleeps_when_delay_positive():
    state = RetryState(job_name="x", max_attempts=3, delay_seconds=1.5)
    mock_sleep = MagicMock()
    wait_before_retry(state, _sleep=mock_sleep)
    mock_sleep.assert_called_once_with(1.5)


def test_wait_before_retry_skips_sleep_when_zero():
    state = RetryState(job_name="x", max_attempts=3, delay_seconds=0)
    mock_sleep = MagicMock()
    wait_before_retry(state, _sleep=mock_sleep)
    mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# run_with_retry
# ---------------------------------------------------------------------------

def test_run_with_retry_succeeds_first_attempt():
    job = _job(retry_attempts=3)
    runner = MagicMock(return_value={"exit_code": 0})
    result, state = run_with_retry(job, runner, _sleep=MagicMock())
    assert result["exit_code"] == 0
    runner.assert_called_once_with(job)
    assert state.attempt == 0


def test_run_with_retry_retries_on_failure():
    job = _job(retry_attempts=3, retry_delay_seconds=0)
    responses = [{"exit_code": 1}, {"exit_code": 1}, {"exit_code": 0}]
    runner = MagicMock(side_effect=responses)
    result, state = run_with_retry(job, runner, _sleep=MagicMock())
    assert result["exit_code"] == 0
    assert runner.call_count == 3


def test_run_with_retry_stops_after_max_attempts():
    job = _job(retry_attempts=2, retry_delay_seconds=0)
    runner = MagicMock(return_value={"exit_code": 1})
    result, state = run_with_retry(job, runner, _sleep=MagicMock())
    assert result["exit_code"] == 1
    assert state.exhausted is True
    assert runner.call_count == 2
