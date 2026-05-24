"""Tests for cronwatcher.webhook."""

from __future__ import annotations

import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.config import AlertConfig
from cronwatcher.webhook import _build_payload, send_webhook_alert


# ---------------------------------------------------------------------------
# _build_payload
# ---------------------------------------------------------------------------

def test_build_payload_failed_job():
    p = _build_payload("backup", 1, "disk full", 12.5)
    assert p["job"] == "backup"
    assert p["exit_code"] == 1
    assert p["stderr"] == "disk full"
    assert p["duration_seconds"] == 12.5
    assert p["status"] == "failed"


def test_build_payload_successful_job():
    p = _build_payload("cleanup", 0, "", 0.123)
    assert p["status"] == "success"
    assert p["exit_code"] == 0


def test_build_payload_rounds_duration():
    p = _build_payload("job", 0, "", 1.123456789)
    assert p["duration_seconds"] == 1.123


# ---------------------------------------------------------------------------
# send_webhook_alert — no URL configured
# ---------------------------------------------------------------------------

def test_send_webhook_no_url_returns_false():
    cfg = AlertConfig(enabled=True, webhook_url=None)
    result = send_webhook_alert(cfg, "job", 1, "err", 1.0)
    assert result is False


def test_send_webhook_empty_url_returns_false():
    cfg = AlertConfig(enabled=True, webhook_url="   ")
    result = send_webhook_alert(cfg, "job", 1, "err", 1.0)
    assert result is False


# ---------------------------------------------------------------------------
# send_webhook_alert — successful POST
# ---------------------------------------------------------------------------

def _mock_response(status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_send_webhook_success():
    cfg = AlertConfig(enabled=True, webhook_url="http://example.com/hook")
    with patch("urllib.request.urlopen", return_value=_mock_response(200)) as mock_open:
        result = send_webhook_alert(cfg, "myjob", 1, "oops", 3.0)
    assert result is True
    mock_open.assert_called_once()
    req = mock_open.call_args[0][0]
    body = json.loads(req.data.decode())
    assert body["job"] == "myjob"
    assert body["exit_code"] == 1


# ---------------------------------------------------------------------------
# send_webhook_alert — error handling
# ---------------------------------------------------------------------------

def test_send_webhook_http_error_returns_false():
    import urllib.error
    cfg = AlertConfig(enabled=True, webhook_url="http://example.com/hook")
    with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
        url="http://example.com/hook", code=500, msg="Server Error",
        hdrs=None, fp=None,
    )):
        result = send_webhook_alert(cfg, "job", 1, "", 1.0)
    assert result is False


def test_send_webhook_url_error_returns_false():
    import urllib.error
    cfg = AlertConfig(enabled=True, webhook_url="http://bad-host/hook")
    with patch("urllib.request.urlopen",
               side_effect=urllib.error.URLError("Name or service not known")):
        result = send_webhook_alert(cfg, "job", 1, "", 1.0)
    assert result is False
