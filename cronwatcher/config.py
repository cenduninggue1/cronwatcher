"""Configuration loading for cronwatcher."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

import yaml


@dataclass
class AlertConfig:
    enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_tls: bool = False
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    from_address: str = "cronwatcher@localhost"
    to_addresses: List[str] = field(default_factory=list)


@dataclass
class JobConfig:
    name: str
    command: str
    schedule: str
    timeout: Optional[int] = None
    alert_on_failure: bool = True


@dataclass
class Config:
    db_path: str = "cronwatcher.db"
    log_level: str = "INFO"
    alert: AlertConfig = field(default_factory=AlertConfig)
    jobs: List[JobConfig] = field(default_factory=list)


def _parse_alert(raw: dict) -> AlertConfig:
    return AlertConfig(
        enabled=raw.get("enabled", False),
        smtp_host=raw.get("smtp_host", "localhost"),
        smtp_port=int(raw.get("smtp_port", 25)),
        smtp_tls=raw.get("smtp_tls", False),
        smtp_username=raw.get("smtp_username"),
        smtp_password=raw.get("smtp_password"),
        from_address=raw.get("from_address", "cronwatcher@localhost"),
        to_addresses=raw.get("to_addresses", []),
    )


def _parse_jobs(raw_list: list) -> List[JobConfig]:
    jobs = []
    for item in raw_list:
        jobs.append(
            JobConfig(
                name=item["name"],
                command=item["command"],
                schedule=item["schedule"],
                timeout=item.get("timeout"),
                alert_on_failure=item.get("alert_on_failure", True),
            )
        )
    return jobs


def load_config(path: str) -> Config:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    return Config(
        db_path=raw.get("db_path", "cronwatcher.db"),
        log_level=raw.get("log_level", "INFO"),
        alert=_parse_alert(raw.get("alert", {})),
        jobs=_parse_jobs(raw.get("jobs", [])),
    )
