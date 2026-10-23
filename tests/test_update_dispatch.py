import pytest

from app.services.update_dispatch import process_once
from app.services.update_jobs import status


def test_dispatch_completes_successful_job(tmp_path):
    db = tmp_path / "jobs.sqlite"
    calls = []
    assert process_once(db, 1, lambda: calls.append("ok"), now=100)
    assert calls == ["ok"]
    assert status(db, 1) == ("done", 1)
    assert not process_once(db, 1, lambda: calls.append("again"), now=300)
    assert calls == ["ok"]


def test_failed_job_remains_recoverable(tmp_path):
    db = tmp_path / "jobs.sqlite"

    def fail():
        raise RuntimeError("simulated failure")

    with pytest.raises(RuntimeError):
        process_once(db, 2, fail, now=100)
    assert status(db, 2) == ("processing", 1)
    assert process_once(db, 2, lambda: None, now=300)
    assert status(db, 2) == ("done", 2)
