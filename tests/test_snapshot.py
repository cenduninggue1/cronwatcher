"""Tests for cronwatcher.snapshot."""

from __future__ import annotations

import datetime
import sqlite3
import pytest

from cronwatcher.config import Config, JobConfig, AlertConfig, RetentionConfig
from cronwatcher.db import init_db
from cronwatcher.snapshot import build_snapshot, format_snapshot, JobSnapshot


@pytest.fixture()
def tmp_db(tmp_path):
    p = tmp_path / "cw.db"
    init_db(str(p))
    return str(p)


def _cfg(*jobs: JobConfig) -> Config:
    return Config(
        db_path="unused",
        jobs=list(jobs),
        alert=AlertConfig(enabled=False),
        retention=RetentionConfig(),
    )


def _make_job(name: str, schedule: str = "* * * * *") -> JobConfig:
    return JobConfig(name=name, schedule=schedule, command="true")


def _insert_run(
    db_path: str,
    job_name: str,
    started_at: datetime.datetime,
    finished_at: datetime.datetime | None = None,
    exit_code: int | None = None,
) -> None:
    con = sqlite3.connect(db_path)
    con.execute(
        "INSERT INTO runs (job_name, started_at, finished_at, exit_code, stdout, stderr)"
        " VALUES (?, ?, ?, ?, '', '')",
        (
            job_name,
            started_at.isoformat(),
            finished_at.isoformat() if finished_at else None,
            exit_code,
        ),
    )
    con.commit()
    con.close()


def test_build_snapshot_empty_jobs(tmp_db):
    cfg = _cfg()
    snaps = build_snapshot(cfg, tmp_db)
    assert snaps == []


def test_build_snapshot_no_runs(tmp_db):
    cfg = _cfg(_make_job("backup"))
    snaps = build_snapshot(cfg, tmp_db)
    assert len(snaps) == 1
    s = snaps[0]
    assert s.job_name == "backup"
    assert s.last_run is None
    assert s.is_stale is False  # no schedule threshold set
    assert s.is_hung is False


def test_build_snapshot_recent_successful_run(tmp_db):
    now = datetime.datetime.utcnow()
    cfg = _cfg(_make_job("cleanup"))
    _insert_run(tmp_db, "cleanup", now - datetime.timedelta(minutes=5),
                now - datetime.timedelta(minutes=4), 0)
    snaps = build_snapshot(cfg, tmp_db)
    assert len(snaps) == 1
    s = snaps[0]
    assert s.last_run is not None
    assert s.is_hung is False


def test_build_snapshot_hung_job(tmp_db):
    old_start = datetime.datetime.utcnow() - datetime.timedelta(hours=3)
    cfg = _cfg(_make_job("long-job"))
    _insert_run(tmp_db, "long-job", old_start)  # no finish
    snaps = build_snapshot(cfg, tmp_db)
    assert snaps[0].is_hung is True


def test_format_snapshot_no_jobs():
    result = format_snapshot([])
    assert "No jobs" in result


def test_format_snapshot_contains_job_name(tmp_db):
    cfg = _cfg(_make_job("my-job"))
    snaps = build_snapshot(cfg, tmp_db)
    output = format_snapshot(snaps)
    assert "my-job" in output


def test_format_snapshot_shows_never_for_no_run(tmp_db):
    cfg = _cfg(_make_job("nightly"))
    snaps = build_snapshot(cfg, tmp_db)
    output = format_snapshot(snaps)
    assert "never" in output
