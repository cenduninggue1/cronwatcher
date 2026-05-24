"""Tests for cronwatcher.cli_tags."""

from __future__ import annotations

import argparse
import sys

import pytest

from cronwatcher.cli_tags import cmd_tags
from cronwatcher.config import Config, JobConfig, AlertConfig, RetentionConfig


def _cfg(jobs):
    return Config(
        db_path=":memory:",
        jobs=jobs,
        alert=AlertConfig(),
        retention=RetentionConfig(),
    )


def _job(name, tags=None):
    return JobConfig(
        name=name, command=f"echo {name}", schedule="* * * * *", tags=tags or []
    )


class _Args:
    def __init__(self, tag=None, list_tags=False):
        self.tag = tag
        self.list_tags = list_tags


def test_list_tags_prints_all(capsys):
    cfg = _cfg([_job("a", ["db"]), _job("b", ["web"])])
    rc = cmd_tags(_Args(list_tags=True), cfg)
    out = capsys.readouterr().out
    assert rc == 0
    assert "db" in out
    assert "web" in out


def test_list_tags_empty(capsys):
    cfg = _cfg([_job("a")])
    rc = cmd_tags(_Args(list_tags=True), cfg)
    out = capsys.readouterr().out
    assert rc == 0
    assert "No tags" in out


def test_filter_by_tag(capsys):
    cfg = _cfg([_job("backup", ["db"]), _job("report", ["web"])])
    rc = cmd_tags(_Args(tag="db"), cfg)
    out = capsys.readouterr().out
    assert rc == 0
    assert "backup" in out
    assert "report" not in out


def test_filter_by_missing_tag_returns_1(capsys):
    cfg = _cfg([_job("a", ["web"])])
    rc = cmd_tags(_Args(tag="db"), cfg)
    assert rc == 1


def test_no_filter_shows_all_groups(capsys):
    cfg = _cfg([_job("a", ["db"]), _job("b")])
    rc = cmd_tags(_Args(), cfg)
    out = capsys.readouterr().out
    assert rc == 0
    assert "(untagged)" in out
    assert "db" in out
