"""Tests for cronwatcher.cli_stale."""

from __future__ import annotations

import argparse
import datetime
import pytest

from cronwatcher.db import init_db, get_connection
from cronwatcher.cli_stale import cmd_stale, add_stale_subparser
from cronwatcher.config import Config, JobConfig, RetentionConfig


@pytest.fixture()
def tmp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    return db_path


def _cfg(db_path: str, jobs=None) -> Config:
    return Config(
        db_path=db_path,
        jobs=jobs or [],
        retention=RetentionConfig(),
    )


def _make_job(name: str, stale_after_minutes: int | None = None) -> JobConfig:
    return JobConfig(
        name=name,
        command="echo hi",
        schedule="* * * * *",
        stale_after_minutes=stale_after_minutes,
    )


def _insert_run(db_path: str, job_name: str, started_at: datetime.datetime) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO runs (job_name, started_at) VALUES (?, ?)",
            (job_name, started_at.isoformat()),
        )


class _Args:
    def __init__(self):
        self.func = cmd_stale


def test_no_stale_jobs_returns_0(tmp_db, capsys):
    job = _make_job("myjob", stale_after_minutes=60)
    _insert_run(tmp_db, "myjob", datetime.datetime.utcnow() - datetime.timedelta(minutes=5))
    cfg = _cfg(tmp_db, [job])
    rc = cmd_stale(_Args(), cfg)
    assert rc == 0
    out = capsys.readouterr().out
    assert "on schedule" in out


def test_stale_jobs_returns_1(tmp_db, capsys):
    job = _make_job("latejob", stale_after_minutes=30)
    cfg = _cfg(tmp_db, [job])  # never run
    rc = cmd_stale(_Args(), cfg)
    assert rc == 1
    out = capsys.readouterr().out
    assert "latejob" in out
    assert "never" in out


def test_add_stale_subparser_registers_command():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_stale_subparser(sub)
    args = parser.parse_args(["stale"])
    assert args.func is cmd_stale
