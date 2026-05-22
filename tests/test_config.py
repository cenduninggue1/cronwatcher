"""Tests for cronwatcher configuration loader."""

import os
import pytest
import tempfile
import yaml

from cronwatcher.config import load_config, Config, JobConfig, AlertConfig


MINIMAL_CONFIG = {
    "jobs": [
        {"name": "test_job", "schedule": "* * * * *", "command": "/bin/true"}
    ]
}

FULL_CONFIG = {
    "log_file": "/tmp/test.log",
    "log_level": "DEBUG",
    "state_dir": "/tmp/cronwatcher_state",
    "alerts": {
        "email": "test@example.com",
        "webhook_url": "https://example.com/hook",
        "slack_channel": "#test",
    },
    "jobs": [
        {
            "name": "job1",
            "schedule": "0 * * * *",
            "command": "/bin/job1.sh",
            "timeout": 120,
            "alert_on_failure": False,
            "alert_on_timeout": True,
            "retries": 3,
        }
    ],
}


@pytest.fixture
def config_file(tmp_path):
    def _write(data):
        path = tmp_path / "cronwatcher.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f)
        return str(path)
    return _write


def test_load_minimal_config(config_file):
    path = config_file(MINIMAL_CONFIG)
    config = load_config(path)
    assert isinstance(config, Config)
    assert len(config.jobs) == 1
    assert config.jobs[0].name == "test_job"
    assert config.jobs[0].timeout == 300
    assert config.jobs[0].retries == 0
    assert config.log_level == "INFO"


def test_load_full_config(config_file):
    path = config_file(FULL_CONFIG)
    config = load_config(path)
    assert config.log_file == "/tmp/test.log"
    assert config.log_level == "DEBUG"
    assert config.alerts.email == "test@example.com"
    assert config.alerts.slack_channel == "#test"
    job = config.jobs[0]
    assert job.name == "job1"
    assert job.timeout == 120
    assert job.retries == 3
    assert job.alert_on_failure is False


def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/config.yaml")


def test_empty_config_raises(config_file, tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("")
    with pytest.raises(ValueError, match="empty"):
        load_config(str(path))


def test_no_jobs_returns_empty_list(config_file):
    path = config_file({"log_level": "WARNING"})
    config = load_config(path)
    assert config.jobs == []
    assert config.log_level == "WARNING"


def test_alerts_defaults_to_none(config_file):
    path = config_file(MINIMAL_CONFIG)
    config = load_config(path)
    assert config.alerts.email is None
    assert config.alerts.webhook_url is None
    assert config.alerts.slack_channel is None
