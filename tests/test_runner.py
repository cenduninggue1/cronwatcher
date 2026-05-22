"""Tests for cronwatcher.runner — subprocess execution + DB persistence."""

import pytest
from pathlib import Path

from cronwatcher import db
from cronwatcher.runner import run_job
from cronwatcher.config import JobConfig


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    path = tmp_path / "runner_test.db"
    db.init_db(path)
    return path


def _make_job(name: str, command: str, timeout: int = 30) -> JobConfig:
    return JobConfig(name=name, command=command, schedule="* * * * *", timeout=timeout)


def test_successful_command(tmp_db: Path):
    job = _make_job("echo_job", "echo hello")
    result = run_job(job, db_path=tmp_db)

    assert result["success"] is True
    assert result["exit_code"] == 0
    assert "hello" in result["stdout"]
    assert result["job_name"] == "echo_job"


def test_failed_command(tmp_db: Path):
    job = _make_job("fail_job", "exit 1")
    result = run_job(job, db_path=tmp_db)

    assert result["success"] is False
    assert result["exit_code"] == 1


def test_result_persisted_to_db(tmp_db: Path):
    job = _make_job("persist_job", "echo stored")
    result = run_job(job, db_path=tmp_db)

    rows = db.get_recent_runs("persist_job", db_path=tmp_db)
    assert len(rows) == 1
    assert rows[0]["id"] == result["run_id"]
    assert rows[0]["success"] == 1


def test_timeout_recorded_as_failure(tmp_db: Path):
    job = _make_job("slow_job", "sleep 10", timeout=1)
    result = run_job(job, db_path=tmp_db, timeout=1)

    assert result["success"] is False
    assert result["exit_code"] == -1
    assert "TimeoutExpired" in result["stderr"]

    rows = db.get_recent_runs("slow_job", db_path=tmp_db)
    assert rows[0]["success"] == 0


def test_duration_is_positive(tmp_db: Path):
    job = _make_job("dur_job", "echo hi")
    result = run_job(job, db_path=tmp_db)
    assert result["duration_seconds"] >= 0
