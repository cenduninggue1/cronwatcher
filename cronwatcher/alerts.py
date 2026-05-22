"""Alert dispatching for cronwatcher."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from cronwatcher.config import AlertConfig

logger = logging.getLogger(__name__)


def _build_subject(job_name: str, exit_code: int) -> str:
    return f"[cronwatcher] Job '{job_name}' failed with exit code {exit_code}"


def _build_body(job_name: str, exit_code: int, stderr: Optional[str]) -> str:
    lines = [
        f"Job:       {job_name}",
        f"Exit code: {exit_code}",
    ]
    if stderr:
        lines.append("\nStderr output:")
        lines.append(stderr.strip())
    return "\n".join(lines)


def send_email_alert(
    cfg: AlertConfig,
    job_name: str,
    exit_code: int,
    stderr: Optional[str] = None,
) -> bool:
    """Send an e-mail alert.  Returns True on success, False on failure."""
    if not cfg.enabled:
        logger.debug("Alerts disabled; skipping e-mail for job '%s'.", job_name)
        return False

    msg = EmailMessage()
    msg["Subject"] = _build_subject(job_name, exit_code)
    msg["From"] = cfg.from_address
    msg["To"] = ", ".join(cfg.to_addresses)
    msg.set_content(_build_body(job_name, exit_code, stderr))

    try:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=10) as smtp:
            if cfg.smtp_tls:
                smtp.starttls()
            if cfg.smtp_username and cfg.smtp_password:
                smtp.login(cfg.smtp_username, cfg.smtp_password)
            smtp.send_message(msg)
        logger.info("Alert e-mail sent for job '%s'.", job_name)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send alert e-mail for job '%s': %s", job_name, exc)
        return False


def dispatch_alert(
    cfg: AlertConfig,
    job_name: str,
    exit_code: int,
    stderr: Optional[str] = None,
) -> bool:
    """Top-level dispatcher — extend here for Slack, PagerDuty, etc."""
    return send_email_alert(cfg, job_name, exit_code, stderr)
