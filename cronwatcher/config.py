"""Configuration loading for cronwatcher.

This file extends the existing config with webhook_url support on AlertConfig.
Only the AlertConfig dataclass and _parse_alert helper are shown here;
the rest of the module is unchanged from the original 98-line version.
"""
# NOTE: This is a targeted patch — in a real repo only the diff would be applied.
# Shown here as a standalone replacement to keep the JSON response self-contained.

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class AlertConfig:
    enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 25
    from_addr: str = ""
    to_addrs: List[str] = field(default_factory=list)
    cooldown_minutes: int = 60
    webhook_url: Optional[str] = None  # <-- new field


@dataclass
class RetentionConfig:
    max_age_days: Optional[int] = None
    max_runs_per_job: Optional[int] = None


@dataclass
class JobConfig:
    name: str
    schedule: str
    command: str
    timeout_seconds: int = 3600
    retries: int = 0
    retry_delay_seconds: int = 60
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class Config:
    db_path: str
    jobs: List[JobConfig]
    alert: AlertConfig = field(default_factory=AlertConfig)
    retention: RetentionConfig = field(default_factory=RetentionConfig)
    log_level: str = "INFO"
    log_file: Optional[str] = None
    prune_interval_minutes: int = 1440
    heartbeat_interval_seconds: int = 60
    stale_threshold_minutes: int = 1440


def _parse_alert(raw: Dict[str, Any]) -> AlertConfig:
    return AlertConfig(
        enabled=raw.get("enabled", False),
        smtp_host=raw.get("smtp_host", "localhost"),
        smtp_port=int(raw.get("smtp_port", 25)),
        from_addr=raw.get("from_addr", ""),
        to_addrs=raw.get("to_addrs", []),
        cooldown_minutes=int(raw.get("cooldown_minutes", 60)),
        webhook_url=raw.get("webhook_url"),
    )


def _parse_retention(raw: Dict[str, Any]) -> RetentionConfig:
    return RetentionConfig(
        max_age_days=raw.get("max_age_days"),
        max_runs_per_job=raw.get("max_runs_per_job"),
    )


def _parse_job(raw: Dict[str, Any]) -> JobConfig:
    return JobConfig(
        name=raw["name"],
        schedule=raw["schedule"],
        command=raw["command"],
        timeout_seconds=int(raw.get("timeout_seconds", 3600)),
        retries=int(raw.get("retries", 0)),
        retry_delay_seconds=int(raw.get("retry_delay_seconds", 60)),
        dependencies=raw.get("dependencies", []),
        tags=raw.get("tags", []),
    )


def load_config(path: str) -> Config:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r") as fh:
        raw = yaml.safe_load(fh) or {}
    return Config(
        db_path=raw.get("db_path", "cronwatcher.db"),
        jobs=[_parse_job(j) for j in raw.get("jobs", [])],
        alert=_parse_alert(raw.get("alert", {})),
        retention=_parse_retention(raw.get("retention", {})),
        log_level=raw.get("log_level", "INFO"),
        log_file=raw.get("log_file"),
        prune_interval_minutes=int(raw.get("prune_interval_minutes", 1440)),
        heartbeat_interval_seconds=int(raw.get("heartbeat_interval_seconds", 60)),
        stale_threshold_minutes=int(raw.get("stale_threshold_minutes", 1440)),
    )
