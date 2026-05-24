"""Webhook alert dispatcher for cronwatcher."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any, Dict

from cronwatcher.config import AlertConfig
from cronwatcher.logging_setup import get_logger

logger = get_logger(__name__)


def _build_payload(job_name: str, exit_code: int, stderr: str, duration: float) -> Dict[str, Any]:
    """Build the JSON payload sent to the webhook endpoint."""
    return {
        "job": job_name,
        "exit_code": exit_code,
        "stderr": stderr,
        "duration_seconds": round(duration, 3),
        "status": "failed" if exit_code != 0 else "success",
    }


def send_webhook_alert(
    cfg: AlertConfig,
    job_name: str,
    exit_code: int,
    stderr: str,
    duration: float,
) -> bool:
    """POST a JSON payload to cfg.webhook_url.

    Returns True on success, False on any network or HTTP error.
    """
    url = (cfg.webhook_url or "").strip()
    if not url:
        logger.debug("Webhook alert skipped: no webhook_url configured.")
        return False

    payload = _build_payload(job_name, exit_code, stderr, duration)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            logger.info("Webhook alert sent to %s (HTTP %s).", url, status)
            return True
    except urllib.error.HTTPError as exc:
        logger.error("Webhook HTTP error %s for %s: %s", exc.code, url, exc.reason)
    except urllib.error.URLError as exc:
        logger.error("Webhook URL error for %s: %s", url, exc.reason)
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected webhook error for %s: %s", url, exc)
    return False
