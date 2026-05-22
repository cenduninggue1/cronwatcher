"""Tests for cronwatcher.alerts."""

from __future__ import annotations

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.alerts import (
    _build_body,
    _build_subject,
    dispatch_alert,
    send_email_alert,
)
from cronwatcher.config import AlertConfig


@pytest.fixture()
def enabled_cfg() -> AlertConfig:
    return AlertConfig(
        enabled=True,
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_tls=True,
        smtp_username="user",
        smtp_password="secret",
        from_address="alerts@example.com",
        to_addresses=["ops@example.com", "dev@example.com"],
    )


@pytest.fixture()
def disabled_cfg() -> AlertConfig:
    return AlertConfig(enabled=False)


def test_build_subject():
    assert "backup" in _build_subject("backup", 1)
    assert "1" in _build_subject("backup", 1)


def test_build_body_with_stderr():
    body = _build_body("myjob", 2, "something went wrong")
    assert "myjob" in body
    assert "2" in body
    assert "something went wrong" in body


def test_build_body_without_stderr():
    body = _build_body("myjob", 2, None)
    assert "Stderr" not in body


def test_send_email_disabled(disabled_cfg):
    result = send_email_alert(disabled_cfg, "job", 1)
    assert result is False


def test_send_email_success(enabled_cfg):
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: s
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch("smtplib.SMTP", return_value=mock_smtp) as smtp_cls:
        result = send_email_alert(enabled_cfg, "backup", 1, stderr="oops")

    assert result is True
    smtp_cls.assert_called_once_with("smtp.example.com", 587, timeout=10)
    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once_with("user", "secret")
    mock_smtp.send_message.assert_called_once()


def test_send_email_smtp_error(enabled_cfg):
    with patch("smtplib.SMTP", side_effect=smtplib.SMTPException("refused")):
        result = send_email_alert(enabled_cfg, "backup", 1)

    assert result is False


def test_dispatch_alert_delegates(enabled_cfg):
    with patch("cronwatcher.alerts.send_email_alert", return_value=True) as mock_send:
        result = dispatch_alert(enabled_cfg, "nightly", 127, stderr="err")

    assert result is True
    mock_send.assert_called_once_with(enabled_cfg, "nightly", 127, "err")
