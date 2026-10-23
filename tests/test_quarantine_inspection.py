from app.services.update_jobs import enqueue, acquire
from app.services.update_quarantine import quarantine_if_exhausted
from app.services.quarantine_inspection import list_quarantined
import pytest


def test_inspection_exposes_only_update_ids_and_attempt_counts(tmp_path):
    db = tmp_path / "queue.sqlite"
    assert list_quarantined(db) == []
    enqueue(db, 9)
    for n in range(3):
        assert acquire(db, 9, now=100 + n * 200)
    assert quarantine_if_exhausted(db, 9)
    assert list_quarantined(db) == [{"update_id": 9, "attempts": 3}]


def test_inspection_rejects_unbounded_queries(tmp_path):
    with pytest.raises(ValueError):
        list_quarantined(tmp_path / "queue.sqlite", limit=1000)
