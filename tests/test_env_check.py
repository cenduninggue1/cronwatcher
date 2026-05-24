"""Tests for cronwatcher.env_check."""
from __future__ import annotations

import os
import shutil
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from cronwatcher.env_check import CheckResult, check_all_jobs, check_job_environment


def _job(
    name="test-job",
    required_env=None,
    required_executables=None,
    required_paths=None,
):
    return SimpleNamespace(
        name=name,
        required_env=required_env or [],
        required_executables=required_executables or [],
        required_paths=required_paths or [],
    )


# ---------------------------------------------------------------------------
# CheckResult helpers
# ---------------------------------------------------------------------------

def test_check_result_ok_when_empty():
    r = CheckResult(job_name="j")
    assert r.ok


def test_check_result_not_ok_with_missing_var():
    r = CheckResult(job_name="j", missing_vars=["FOO"])
    assert not r.ok


def test_check_result_str_contains_job_name():
    r = CheckResult(job_name="my-job")
    assert "my-job" in str(r)


# ---------------------------------------------------------------------------
# check_job_environment
# ---------------------------------------------------------------------------

def test_no_requirements_passes():
    result = check_job_environment(_job())
    assert result.ok


def test_missing_env_var_detected():
    env_var = "__CRONWATCHER_MISSING_VAR_XYZ__"
    os.environ.pop(env_var, None)
    result = check_job_environment(_job(required_env=[env_var]))
    assert env_var in result.missing_vars
    assert not result.ok


def test_present_env_var_passes():
    os.environ["__CRONWATCHER_PRESENT__"] = "1"
    result = check_job_environment(_job(required_env=["__CRONWATCHER_PRESENT__"]))
    assert result.ok
    del os.environ["__CRONWATCHER_PRESENT__"]


def test_missing_executable_detected():
    result = check_job_environment(
        _job(required_executables=["__no_such_exe_cronwatcher__"])
    )
    assert "__no_such_exe_cronwatcher__" in result.missing_executables
    assert not result.ok


def test_present_executable_passes():
    exe = "python" if shutil.which("python") else sys.executable.split("/")[-1]
    result = check_job_environment(_job(required_executables=[exe]))
    assert exe not in result.missing_executables


def test_missing_path_detected(tmp_path):
    missing = str(tmp_path / "does_not_exist")
    result = check_job_environment(_job(required_paths=[missing]))
    assert missing in result.missing_paths
    assert not result.ok


def test_existing_path_passes(tmp_path):
    result = check_job_environment(_job(required_paths=[str(tmp_path)]))
    assert result.ok


# ---------------------------------------------------------------------------
# check_all_jobs
# ---------------------------------------------------------------------------

def test_check_all_jobs_returns_one_result_per_job():
    jobs = [_job(name="a"), _job(name="b"), _job(name="c")]
    results = check_all_jobs(jobs)
    assert len(results) == 3
    assert [r.job_name for r in results] == ["a", "b", "c"]


def test_check_all_jobs_empty_list():
    assert check_all_jobs([]) == []
