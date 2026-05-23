"""Tests for the cronwatcher daemon loop."""
from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from cronwatcher.daemon import _seconds_until_next_minute, run_daemon


@pytest.fixture()
def config_file(tmp_path: Path) -> Path:
    cfg = tmp_path / "cronwatcher.yaml"
    cfg.write_text(
        textwrap.dedent(
            """\
            database_path: {db}
            jobs:
              - name: tick
                command: echo tick
                schedule: "* * * * *"
            """.format(db=str(tmp_path / "cw.db"))
        )
    )
    return cfg


def test_seconds_until_next_minute_in_range() -> None:
    val = _seconds_until_next_minute()
    assert 0.0 <= val <= 60.0


def test_daemon_runs_and_stops(config_file: Path) -> None:
    """Daemon should call run_due_jobs once then stop when _STOP is set."""
    import cronwatcher.daemon as daemon_mod

    run_count = 0

    def fake_run_due_jobs(cfg, conn):
        nonlocal run_count
        run_count += 1
        daemon_mod._STOP = True  # stop after first tick

    with (
        patch("cronwatcher.daemon.time.sleep"),
        patch("cronwatcher.daemon.run_due_jobs", side_effect=fake_run_due_jobs),
        patch("cronwatcher.daemon.prune_runs", return_value=0),
    ):
        run_daemon(config_file, tick_interval=0.0, prune_interval_ticks=1)

    assert run_count == 1


def test_daemon_prunes_on_interval(config_file: Path) -> None:
    import cronwatcher.daemon as daemon_mod

    tick = 0

    def fake_run(cfg, conn):
        nonlocal tick
        tick += 1
        if tick >= 2:
            daemon_mod._STOP = True

    prune_mock = MagicMock(return_value=0)

    with (
        patch("cronwatcher.daemon.time.sleep"),
        patch("cronwatcher.daemon.run_due_jobs", side_effect=fake_run),
        patch("cronwatcher.daemon.prune_runs", prune_mock),
    ):
        run_daemon(config_file, tick_interval=0.0, prune_interval_ticks=1)

    assert prune_mock.call_count >= 1


def test_daemon_survives_tick_exception(config_file: Path) -> None:
    import cronwatcher.daemon as daemon_mod

    tick = 0

    def flaky_run(cfg, conn):
        nonlocal tick
        tick += 1
        if tick == 1:
            raise RuntimeError("boom")
        daemon_mod._STOP = True

    with (
        patch("cronwatcher.daemon.time.sleep"),
        patch("cronwatcher.daemon.run_due_jobs", side_effect=flaky_run),
        patch("cronwatcher.daemon.prune_runs", return_value=0),
    ):
        # Should not raise
        run_daemon(config_file, tick_interval=0.0, prune_interval_ticks=100)

    assert tick == 2
