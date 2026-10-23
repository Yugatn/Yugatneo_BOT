"""Offline retry and quarantine integration regression."""
import asyncio
import sqlite3

from app.services.async_update_dispatch import dispatch_update
from app.services.update_jobs import status
from app.services.update_quarantine import quarantine_if_exhausted
from app.services.update_operations import release_quarantined


def test_retry_quarantine_and_manual_release(tmp_path):
    db = tmp_path / "queue.sqlite"
    attempts = []

    async def failing_handler():
        attempts.append("failed")
        raise RuntimeError("handler failure")

    for number in range(3):
        try:
            asyncio.run(dispatch_update(db, 101, failing_handler))
        except RuntimeError:
            pass
        else:
            raise AssertionError("Handler must fail")
        if number < 2:
            with sqlite3.connect(db) as conn:
                conn.execute("UPDATE update_jobs SET lease_until=0 WHERE update_id=101")

    assert status(db, 101) == ("processing", 3)
    assert quarantine_if_exhausted(db, 101)
    assert not asyncio.run(dispatch_update(db, 101, failing_handler))
    assert len(attempts) == 3
    assert release_quarantined(db, 101, operator_approved=True)

    async def successful_handler():
        attempts.append("ok")

    assert asyncio.run(dispatch_update(db, 101, successful_handler))
    assert status(db, 101) == ("done", 4)
    assert attempts[-1] == "ok"
