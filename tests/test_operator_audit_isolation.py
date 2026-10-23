"""Regression: user deletion must never change operational audit entries."""
import sqlite3

from app.services.personal_data import delete_telegram_user_records
from app.services.update_jobs import enqueue, acquire
from app.services.update_quarantine import quarantine_if_exhausted
from app.services.update_operations import release_quarantined


def test_user_deletion_cannot_modify_operator_audit(tmp_path):
    db = tmp_path / "bot.sqlite"
    enqueue(db, 55)
    for n in range(3):
        assert acquire(db, 55, now=100 + n * 200)
    assert quarantine_if_exhausted(db, 55)
    assert release_quarantined(db, 55, operator_approved=True)
    with sqlite3.connect(db) as conn:
        before = conn.execute(
            "SELECT update_id,action,created_at FROM update_operator_audit"
        ).fetchall()
    delete_telegram_user_records(db, "55")
    with sqlite3.connect(db) as conn:
        after = conn.execute(
            "SELECT update_id,action,created_at FROM update_operator_audit"
        ).fetchall()
    assert before == after
    assert len(after) == 1
