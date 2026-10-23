import sqlite3
import pytest

from app.services.update_jobs import enqueue, acquire, status
from app.services.update_quarantine import quarantine_if_exhausted
from app.services.update_operations import update_metrics, release_quarantined


def test_operator_can_release_quarantine(tmp_path):
    db = tmp_path / "jobs.sqlite"
    enqueue(db, 100)
    for index in range(3):
        assert acquire(db, 100, now=100 + index * 200)
    assert quarantine_if_exhausted(db, 100)
    assert update_metrics(db)["states"] == {"quarantined": 1}
    with pytest.raises(PermissionError):
        release_quarantined(db, 100)
    assert release_quarantined(db, 100, operator_approved=True)
    assert status(db, 100) == ("pending", 3)
    assert acquire(db, 100, now=1000)
    assert not release_quarantined(db, 100, operator_approved=True)
    with sqlite3.connect(db) as conn:
        rows = conn.execute('SELECT update_id,action FROM update_operator_audit').fetchall()
    assert rows == [(100, 'release_quarantine')]


def test_empty_queue_metrics(tmp_path):
    assert update_metrics(tmp_path / "empty.sqlite") == {"total": 0, "states": {}}
