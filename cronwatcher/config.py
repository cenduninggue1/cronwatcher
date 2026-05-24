"""Configuration loading and validation for cronwatcher.

Extended to support an optional ``tags`` field on each JobConfig.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

import yaml


@dataclass
class AlertConfig:
    enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 25
    from_addr: str = ""
    to_addrs: list[str] = field(default_factory=list)
    cooldown_minutes: int = 60


@dataclass
class RetentionConfig:
    max_age_days: Optional[int] = None
    max_runs_per_job: Optional[int] = None


@dataclass
class JobConfig:
    name: str
    command: str
    schedule: str
    timeout_seconds: Optional[int] = None
    tags: list[str] = field(default_factory=list)


@dataclass
class Config:
    db_path: str
    jobs: list[JobConfig]
    alert: AlertConfig = field(default_factory=AlertConfig)
    retention: RetentionConfig = field(default_factory=RetentionConfig)
    log_level: str = "INFO"
    prune_interval_minutes: int = 60


def _parse_alert(raw: dict[str, Any]) -> AlertConfig:
    return AlertConfig(
        enabled=raw.get("enabled", False),
        smtp_host=raw.get("smtp_host", "localhost"),
        smtp_port=int(raw.get("smtp_port", 25)),
        from_addr=raw.get("from_addr", ""),
        to_addrs=raw.get("to_addrs", []),
        cooldown_minutes=int(raw.get("cooldown_minutes", 60)),
    )


def _parse_retention(raw: dict[str, Any]) -> RetentionConfig:
    return RetentionConfig(
        max_age_days=raw.get("max_age_days"),
        max_runs_per_job=raw.get("max_runs_per_job"),
    )


def _parse_job(raw: dict[str, Any]) -> JobConfig:
    tags_raw = raw.get("tags", [])
    if isinstance(tags_raw, str):
        tags_raw = [t.strip() for t in tags_raw.split(",") if t.strip()]
    return JobConfig(
        name=raw["name"],
        command=raw["command"],
        schedule=raw["schedule"],
        timeout_seconds=raw.get("timeout_seconds"),
        tags=tags_raw,
    )


def load_config(path: str) -> Config:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path) as fh:
        raw = yaml.safe_load(fh) or {}

    jobs = [_parse_job(j) for j in raw.get("jobs", [])]
    alert = _parse_alert(raw.get("alert", {}))
    retention = _parse_retention(raw.get("retention", {}))

    return Config(
        db_path=raw.get("db_path", "cronwatcher.db"),
        jobs=jobs,
        alert=alert,
        retention=retention,
        log_level=raw.get("log_level", "INFO"),
        prune_interval_minutes=int(raw.get("prune_interval_minutes", 60)),
    )
