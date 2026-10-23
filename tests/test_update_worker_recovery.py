"""Simulate process death while a Telegram update lease is held."""
import subprocess
import sys

from app.services.update_jobs import enqueue, acquire, complete, status


def test_crashed_worker_can_resume_after_lease(tmp_path):
    db = tmp_path / "jobs.sqlite"
    enqueue(db, 44)
    code = (
        "from app.services.update_jobs import acquire; import os; "
        "assert acquire(os.environ['TEST_DB'],44,now=100,lease_seconds=10); "
        "os._exit(7)"
    )
    import os
    env = dict(os.environ, TEST_DB=str(db))
    run = subprocess.run([sys.executable, "-c", code], env=env, check=False)
    assert run.returncode == 7
    assert status(db, 44) == ("processing", 1)
    assert not acquire(db, 44, now=105)
    assert acquire(db, 44, now=111)
    complete(db, 44)
    assert status(db, 44) == ("done", 2)
