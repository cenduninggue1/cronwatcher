"""SQLite-backed storage for cron job execution records."""

import sqlite3
import contextlib
from datetime import datetime
from pathlib import Path
from typing import Optional


DEFAULT_DB_PATH = Path("/var/lib/cronwatcher/jobs.db")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS job_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name    TEXT    NOT NULL,
    started_at  TEXT    NOT NULL,
    finished_at TEXT,
    exit_code   INTEGER,
    stdout      TEXT,
    stderr      TEXT,
    success     INTEGER NOT NULL DEFAULT 0
);
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


@contextlib.contextmanager
def get_connection(db_path: Path = DEFAULT_DB_PATH):
    conn = _connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Create schema if it does not exist."""
    with get_connection(db_path) as conn:
        conn.execute(CREATE_TABLE_SQL)


def record_start(job_name: str, started_at: datetime, db_path: Path = DEFAULT_DB_PATH) -> int:
    """Insert a new run record and return its row id."""
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO job_runs (job_name, started_at, success) VALUES (?, ?, 0)",
            (job_name, started_at.isoformat()),
        )
        return cur.lastrowid


def record_finish(
    run_id: int,
    finished_at: datetime,
    exit_code: int,
    stdout: str,
    stderr: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Update an existing run record with completion details."""
    success = 1 if exit_code == 0 else 0
    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE job_runs
               SET finished_at = ?, exit_code = ?, stdout = ?, stderr = ?, success = ?
             WHERE id = ?
            """,
            (finished_at.isoformat(), exit_code, stdout, stderr, success, run_id),
        )


def get_recent_runs(job_name: str, limit: int = 10, db_path: Path = DEFAULT_DB_PATH) -> list:
    """Return the most recent runs for a given job."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM job_runs WHERE job_name = ? ORDER BY id DESC LIMIT ?",
            (job_name, limit),
        ).fetchall()
    return [dict(r) for r in rows]
