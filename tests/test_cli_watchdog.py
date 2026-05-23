"""Tests for cronwatcher.cli_watchdog."""

from __future__ import annotations

import datetime
import textwrap

import pytest

from cronwatcher.db import init_db, get_connection
from cronwatcher.cli_watchdog import cmd_watchdog


@pytest.fixture()
def config_file(tmp_path):
    db = tmp_path / "cw.db"
    init_db(str(db))
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        textwrap.dedent(
            f"""\
            db_path: {db}
            jobs: []
            """
        )
    )
    return cfg, db


class _Args:
    def __init__(self, config, timeout=3600, fix=False):
        self.config = str(config)
        self.timeout = timeout
        self.fix = fix


def _insert_unfinished(db_path: str, job_name: str, started_at: datetime.datetime) -> int:
    con = get_connection(str(db_path))
    cur = con.execute(
        "INSERT INTO runs (job_name, started_at) VALUES (?, ?)",
        (job_name, started_at.isoformat()),
    )
    con.commit()
    run_id = cur.lastrowid
    con.close()
    return run_id


def test_watchdog_no_hung_jobs(config_file):
    cfg_path, _ = config_file
    rc = cmd_watchdog(_Args(cfg_path))
    assert rc == 0


def test_watchdog_missing_config(tmp_path):
    rc = cmd_watchdog(_Args(tmp_path / "missing.yaml"))
    assert rc == 2


def test_watchdog_lists_hung_jobs(config_file, capsys):
    cfg_path, db_path = config_file
    ref = datetime.datetime.utcnow()
    old = ref - datetime.timedelta(hours=2)
    _insert_unfinished(str(db_path), "nightly-report", old)

    rc = cmd_watchdog(_Args(cfg_path, timeout=3600))
    assert rc == 1
    captured = capsys.readouterr()
    assert "nightly-report" in captured.out
    assert "Found" in captured.out


def test_watchdog_fix_marks_jobs(config_file, capsys):
    cfg_path, db_path = config_file
    ref = datetime.datetime.utcnow()
    old = ref - datetime.timedelta(hours=3)
    run_id = _insert_unfinished(str(db_path), "etl", old)

    rc = cmd_watchdog(_Args(cfg_path, timeout=3600, fix=True))
    assert rc == 1
    captured = capsys.readouterr()
    assert "Marked" in captured.out

    con = get_connection(str(db_path))
    row = con.execute(
        "SELECT exit_code FROM runs WHERE id = ?", (run_id,)
    ).fetchone()
    con.close()
    assert row["exit_code"] == -1
