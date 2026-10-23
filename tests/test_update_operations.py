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
    assert release_quarantined(db, 100)
    assert status(db, 100) == ("pending", 3)
    assert acquire(db, 100, now=1000)
    assert not release_quarantined(db, 100)


def test_empty_queue_metrics(tmp_path):
    assert update_metrics(tmp_path / "empty.sqlite") == {"total": 0, "states": {}}
