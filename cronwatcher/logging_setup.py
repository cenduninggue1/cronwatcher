"""Logging configuration helpers for cronwatcher."""
from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

_DEFAULT_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(
    *,
    level: str = "INFO",
    log_file: Optional[Path] = None,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
    fmt: str = _DEFAULT_FORMAT,
    datefmt: str = _DEFAULT_DATE_FORMAT,
) -> None:
    """Configure the root logger for cronwatcher.

    Parameters
    ----------
    level:
        Logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    log_file:
        Optional path to a rotating log file.  When *None* only the
        console handler is attached.
    max_bytes:
        Maximum size of a single log file before rotation.
    backup_count:
        Number of rotated log files to keep.
    fmt:
        Log record format string.
    datefmt:
        Date/time format string.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    root = logging.getLogger()
    root.setLevel(numeric_level)

    # Remove any handlers already attached (idempotent reconfiguration).
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()

    # Console handler.
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    console.setLevel(numeric_level)
    root.addHandler(console)

    # Optional rotating file handler.
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(numeric_level)
        root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger namespaced under *cronwatcher*."""
    if not name.startswith("cronwatcher"):
        name = f"cronwatcher.{name}"
    return logging.getLogger(name)
