from app.services.update_jobs import enqueue, acquire, status
from app.services.update_quarantine import quarantine_if_exhausted


def test_repeated_failure_quarantines_update(tmp_path):
    db = tmp_path / "jobs.sqlite"
    enqueue(db, 50)
    for attempt in range(3):
        assert acquire(db, 50, now=100 + attempt * 200)
    assert quarantine_if_exhausted(db, 50)
    assert status(db, 50) == ("quarantined", 3)
    assert not acquire(db, 50, now=1000)


def test_single_failure_does_not_quarantine(tmp_path):
    db = tmp_path / "jobs.sqlite"
    enqueue(db, 60)
    assert acquire(db, 60, now=100)
    assert not quarantine_if_exhausted(db, 60)
