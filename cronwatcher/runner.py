"""Execute a cron job command and persist the result via db module."""

import subprocess
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cronwatcher.config import JobConfig
from cronwatcher import db

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def run_job(
    job: JobConfig,
    db_path: Path = db.DEFAULT_DB_PATH,
    timeout: Optional[int] = None,
) -> dict:
    """
    Execute *job.command* in a subprocess, record start/finish in the DB,
    and return a result dict with keys: run_id, job_name, exit_code, success,
    stdout, stderr, duration_seconds.
    """
    started_at = _utcnow()
    run_id = db.record_start(job.name, started_at, db_path=db_path)

    logger.info("[%s] starting (run_id=%d): %s", job.name, run_id, job.command)

    try:
        proc = subprocess.run(
            job.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout or job.timeout,
        )
        exit_code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = -1
        stdout = ""
        stderr = f"TimeoutExpired after {exc.timeout}s"
        logger.error("[%s] timed out after %ss", job.name, exc.timeout)
    except Exception as exc:  # noqa: BLE001
        exit_code = -2
        stdout = ""
        stderr = str(exc)
        logger.exception("[%s] unexpected error", job.name)

    finished_at = _utcnow()
    duration = (finished_at - started_at).total_seconds()

    db.record_finish(
        run_id,
        finished_at,
        exit_code,
        stdout,
        stderr,
        db_path=db_path,
    )

    success = exit_code == 0
    level = logging.INFO if success else logging.ERROR
    logger.log(level, "[%s] finished in %.2fs — exit_code=%d", job.name, duration, exit_code)

    return {
        "run_id": run_id,
        "job_name": job.name,
        "exit_code": exit_code,
        "success": success,
        "stdout": stdout,
        "stderr": stderr,
        "duration_seconds": duration,
    }
