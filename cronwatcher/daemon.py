"""Simple blocking daemon loop for cronwatcher."""
from __future__ import annotations

import logging
import signal
import time
from datetime import datetime, timezone
from pathlib import Path
from types import FrameType
from typing import Optional

from cronwatcher.config import Config
from cronwatcher.db import get_connection, init_db
from cronwatcher.retention import prune_runs
from cronwatcher.scheduler import run_due_jobs

logger = logging.getLogger(__name__)

_STOP = False


def _handle_signal(signum: int, frame: Optional[FrameType]) -> None:  # noqa: ARG001
    global _STOP
    logger.info("Received signal %s — stopping after current tick.", signum)
    _STOP = True


def _seconds_until_next_minute() -> float:
    """Return the number of seconds until the start of the next minute."""
    now = datetime.now(tz=timezone.utc)
    return 60.0 - now.second - now.microsecond / 1_000_000


def run_daemon(
    config_path: Path,
    *,
    tick_interval: float = 60.0,
    prune_interval_ticks: int = 60,
) -> None:
    """Start the blocking daemon loop.

    Loads configuration once, then ticks every *tick_interval* seconds,
    running any due jobs.  Retention pruning is performed every
    *prune_interval_ticks* ticks.
    """
    global _STOP
    _STOP = False

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    cfg = Config.load(config_path)
    logger.info("cronwatcher daemon starting (db=%s).", cfg.database_path)

    with get_connection(cfg.database_path) as conn:
        init_db(conn)

    tick_count = 0

    # Align to the next whole minute before entering the loop.
    sleep_for = _seconds_until_next_minute()
    logger.debug("Sleeping %.1fs to align to minute boundary.", sleep_for)
    time.sleep(sleep_for)

    while not _STOP:
        tick_start = time.monotonic()
        tick_count += 1

        try:
            with get_connection(cfg.database_path) as conn:
                run_due_jobs(cfg, conn)

            if tick_count % prune_interval_ticks == 0:
                with get_connection(cfg.database_path) as conn:
                    removed = prune_runs(conn, cfg.retention)
                if removed:
                    logger.info("Pruned %d old run record(s).", removed)
        except Exception:
            logger.exception("Unhandled error during tick %d.", tick_count)

        elapsed = time.monotonic() - tick_start
        sleep_for = max(0.0, tick_interval - elapsed)
        if not _STOP:
            time.sleep(sleep_for)

    logger.info("cronwatcher daemon stopped after %d tick(s).", tick_count)
