from app.services.update_jobs import enqueue, acquire, complete, status


def test_update_job_lease_and_restart_recovery(tmp_path):
    db = tmp_path / "jobs.sqlite"
    enqueue(db, 42)
    assert acquire(db, 42, now=100, lease_seconds=10)
    assert not acquire(db, 42, now=105, lease_seconds=10)
    assert acquire(db, 42, now=111, lease_seconds=10)
    assert status(db, 42) == ("processing", 2)
    complete(db, 42)
    assert status(db, 42) == ("done", 2)
    assert not acquire(db, 42, now=200)


def test_duplicate_enqueue_does_not_reset_completion(tmp_path):
    db = tmp_path / "jobs.sqlite"
    enqueue(db, 7)
    assert acquire(db, 7, now=100)
    complete(db, 7)
    enqueue(db, 7)
    assert status(db, 7) == ("done", 1)
