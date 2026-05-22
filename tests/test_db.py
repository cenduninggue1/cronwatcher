"""Tests for cronwatcher.db — SQLite persistence layer."""

import pytest
from datetime import datetime, timezone
from pathlib import Path

from cronwatcher import db


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    db.init_db(path)
    return path


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def test_init_db_creates_file(tmp_path: Path):
    path = tmp_path / "sub" / "jobs.db"
    db.init_db(path)
    assert path.exists()


def test_record_start_returns_id(tmp_db: Path):
    run_id = db.record_start("backup", _now(), db_path=tmp_db)
    assert isinstance(run_id, int)
    assert run_id >= 1


def test_record_start_increments(tmp_db: Path):
    id1 = db.record_start("job_a", _now(), db_path=tmp_db)
    id2 = db.record_start("job_a", _now(), db_path=tmp_db)
    assert id2 > id1


def test_record_finish_success(tmp_db: Path):
    run_id = db.record_start("myjob", _now(), db_path=tmp_db)
    db.record_finish(run_id, _now(), 0, "ok", "", db_path=tmp_db)

    rows = db.get_recent_runs("myjob", db_path=tmp_db)
    assert len(rows) == 1
    row = rows[0]
    assert row["exit_code"] == 0
    assert row["success"] == 1
    assert row["stdout"] == "ok"


def test_record_finish_failure(tmp_db: Path):
    run_id = db.record_start("myjob", _now(), db_path=tmp_db)
    db.record_finish(run_id, _now(), 1, "", "error!", db_path=tmp_db)

    rows = db.get_recent_runs("myjob", db_path=tmp_db)
    row = rows[0]
    assert row["success"] == 0
    assert row["stderr"] == "error!"


def test_get_recent_runs_limit(tmp_db: Path):
    for _ in range(15):
        rid = db.record_start("batch", _now(), db_path=tmp_db)
        db.record_finish(rid, _now(), 0, "", "", db_path=tmp_db)

    rows = db.get_recent_runs("batch", limit=5, db_path=tmp_db)
    assert len(rows) == 5


def test_get_recent_runs_isolates_jobs(tmp_db: Path):
    rid = db.record_start("job_x", _now(), db_path=tmp_db)
    db.record_finish(rid, _now(), 0, "", "", db_path=tmp_db)

    rows = db.get_recent_runs("job_y", db_path=tmp_db)
    assert rows == []
