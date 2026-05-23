"""Tests for the cronwatcher CLI."""
from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.cli import (
    _build_parser,
    cmd_history,
    cmd_prune,
    cmd_run,
    cmd_summary,
    main,
)


@pytest.fixture()
def config_file(tmp_path: Path) -> Path:
    cfg = tmp_path / "cronwatcher.yaml"
    cfg.write_text(
        textwrap.dedent(
            """\
            database_path: {db}
            jobs:
              - name: hello
                command: echo hello
                schedule: "* * * * *"
            """.format(db=str(tmp_path / "cw.db"))
        )
    )
    return cfg


def test_no_command_returns_1(config_file: Path) -> None:
    rc = main(["-c", str(config_file)])
    assert rc == 1


def test_missing_config_returns_2(tmp_path: Path) -> None:
    rc = main(["-c", str(tmp_path / "missing.yaml"), "run"])
    assert rc == 2


def test_run_command_succeeds(config_file: Path) -> None:
    with patch("cronwatcher.cli.run_due_jobs") as mock_run:
        rc = main(["-c", str(config_file), "run"])
    assert rc == 0
    mock_run.assert_called_once()


def test_summary_no_data(config_file: Path, capsys: pytest.CaptureFixture) -> None:
    rc = main(["-c", str(config_file), "summary"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "No job data" in out


def test_prune_prints_count(config_file: Path, capsys: pytest.CaptureFixture) -> None:
    with patch("cronwatcher.cli.prune_runs", return_value=3):
        rc = main(["-c", str(config_file), "prune"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "3" in out


def test_history_no_runs(config_file: Path, capsys: pytest.CaptureFixture) -> None:
    rc = main(["-c", str(config_file), "history", "hello"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "No runs found" in out


def test_history_shows_runs(config_file: Path, capsys: pytest.CaptureFixture) -> None:
    from datetime import datetime, timezone
    from cronwatcher.history import JobRun

    fake_run = JobRun(
        run_id=1,
        job_name="hello",
        command="echo hello",
        started_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2024, 1, 15, 12, 0, 1, tzinfo=timezone.utc),
        exit_code=0,
        stderr="",
    )
    with patch("cronwatcher.cli.get_recent_runs", return_value=[fake_run]):
        rc = main(["-c", str(config_file), "history", "hello", "-n", "5"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out
    assert "echo hello" in out


def test_parser_history_default_limit() -> None:
    parser = _build_parser()
    args = parser.parse_args(["-c", "cfg.yaml", "history", "myjob"])
    assert args.limit == 10
    assert args.job == "myjob"
