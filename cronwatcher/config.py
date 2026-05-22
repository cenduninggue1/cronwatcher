"""Configuration loader for cronwatcher."""

import os
import yaml
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AlertConfig:
    email: Optional[str] = None
    webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None


@dataclass
class JobConfig:
    name: str
    schedule: str
    command: str
    timeout: int = 300
    alert_on_failure: bool = True
    alert_on_timeout: bool = True
    retries: int = 0


@dataclass
class Config:
    log_file: str = "/var/log/cronwatcher.log"
    log_level: str = "INFO"
    state_dir: str = "/var/lib/cronwatcher"
    alerts: AlertConfig = field(default_factory=AlertConfig)
    jobs: List[JobConfig] = field(default_factory=list)


def load_config(path: str) -> Config:
    """Load configuration from a YAML file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ValueError("Config file is empty")

    alerts_raw = raw.get("alerts", {})
    alerts = AlertConfig(
        email=alerts_raw.get("email"),
        webhook_url=alerts_raw.get("webhook_url"),
        slack_channel=alerts_raw.get("slack_channel"),
    )

    jobs = [
        JobConfig(
            name=j["name"],
            schedule=j["schedule"],
            command=j["command"],
            timeout=j.get("timeout", 300),
            alert_on_failure=j.get("alert_on_failure", True),
            alert_on_timeout=j.get("alert_on_timeout", True),
            retries=j.get("retries", 0),
        )
        for j in raw.get("jobs", [])
    ]

    return Config(
        log_file=raw.get("log_file", "/var/log/cronwatcher.log"),
        log_level=raw.get("log_level", "INFO"),
        state_dir=raw.get("state_dir", "/var/lib/cronwatcher"),
        alerts=alerts,
        jobs=jobs,
    )
