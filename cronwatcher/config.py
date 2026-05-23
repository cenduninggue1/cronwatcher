"""Configuration loading for cronwatcher."""

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
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    from_address: str = "cronwatcher@localhost"
    to_addresses: List[str] = field(default_factory=list)
    use_tls: bool = False


@dataclass
class RetentionConfig:
    max_age_days: Optional[int] = None
    max_rows_per_job: Optional[int] = None


@dataclass
class JobConfig:
    name: str
    command: str
    schedule: str
    timeout: Optional[int] = None
    alert: Optional[AlertConfig] = None


@dataclass
class Config:
    db_path: str
    jobs: List[JobConfig]
    default_alert: Optional[AlertConfig] = None
    retention: RetentionConfig = field(default_factory=RetentionConfig)


def _parse_alert(raw: Dict[str, Any]) -> AlertConfig:
    return AlertConfig(
        enabled=raw.get("enabled", False),
        smtp_host=raw.get("smtp_host", "localhost"),
        smtp_port=int(raw.get("smtp_port", 25)),
        smtp_user=raw.get("smtp_user"),
        smtp_password=raw.get("smtp_password"),
        from_address=raw.get("from_address", "cronwatcher@localhost"),
        to_addresses=raw.get("to_addresses", []),
        use_tls=raw.get("use_tls", False),
    )


def _parse_retention(raw: Dict[str, Any]) -> RetentionConfig:
    return RetentionConfig(
        max_age_days=raw.get("max_age_days"),
        max_rows_per_job=raw.get("max_rows_per_job"),
    )


def _parse_jobs(
    raw_jobs: List[Dict[str, Any]],
    default_alert: Optional[AlertConfig],
) -> List[JobConfig]:
    jobs = []
    for raw in raw_jobs:
        alert = _parse_alert(raw["alert"]) if "alert" in raw else default_alert
        jobs.append(
            JobConfig(
                name=raw["name"],
                command=raw["command"],
                schedule=raw["schedule"],
                timeout=raw.get("timeout"),
                alert=alert,
            )
        )
    return jobs


def load_config(path: str) -> Config:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path) as fh:
        raw = yaml.safe_load(fh) or {}

    default_alert = _parse_alert(raw["alert"]) if "alert" in raw else None
    retention = _parse_retention(raw.get("retention", {}))
    jobs = _parse_jobs(raw.get("jobs", []), default_alert)

    return Config(
        db_path=raw.get("db_path", "cronwatcher.db"),
        jobs=jobs,
        default_alert=default_alert,
        retention=retention,
    )
