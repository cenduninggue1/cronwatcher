"""Tests for cronwatcher.tags."""

from __future__ import annotations

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.tags import (
    format_tag_summary,
    get_all_tags,
    get_jobs_by_tag,
    group_by_tag,
)


def _job(name: str, tags: list[str] | None = None) -> JobConfig:
    return JobConfig(
        name=name,
        command=f"echo {name}",
        schedule="* * * * *",
        tags=tags or [],
    )


def test_get_jobs_by_tag_returns_matching():
    jobs = [_job("a", ["db", "nightly"]), _job("b", ["web"]), _job("c", ["db"])]
    result = get_jobs_by_tag(jobs, "db")
    assert [j.name for j in result] == ["a", "c"]


def test_get_jobs_by_tag_no_match():
    jobs = [_job("a", ["web"])]
    assert get_jobs_by_tag(jobs, "db") == []


def test_get_all_tags_sorted_unique():
    jobs = [_job("a", ["z", "a"]), _job("b", ["a", "m"])]
    assert get_all_tags(jobs) == ["a", "m", "z"]


def test_get_all_tags_empty():
    assert get_all_tags([]) == []


def test_group_by_tag_untagged():
    jobs = [_job("x")]
    groups = group_by_tag(jobs)
    assert "(untagged)" in groups
    assert groups["(untagged)"][0].name == "x"


def test_group_by_tag_multiple_tags():
    job = _job("multi", ["a", "b"])
    groups = group_by_tag([job])
    assert "multi" in [j.name for j in groups["a"]]
    assert "multi" in [j.name for j in groups["b"]]


def test_format_tag_summary_empty():
    assert format_tag_summary({}) == "No jobs found."


def test_format_tag_summary_renders_lines():
    jobs = [_job("backup"), _job("report")]
    groups = {"nightly": jobs}
    output = format_tag_summary(groups)
    assert "[nightly]" in output
    assert "backup" in output
    assert "report" in output
