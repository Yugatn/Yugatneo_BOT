"""Operational metrics and audited manual recovery for Telegram update jobs."""
import sqlite3


def update_metrics(db_path):
    with sqlite3.connect(db_path) as conn:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='update_jobs'"
        ).fetchone()
        if not exists:
            return {"total": 0, "states": {}}
        states = dict(conn.execute(
            "SELECT state, COUNT(*) FROM update_jobs GROUP BY state"
        ))
        return {"total": sum(states.values()), "states": states}


def release_quarantined(db_path, update_id, *, operator_approved=False):
    """Release one update only after explicit operator approval.

    The audit records no message text or user identifiers.
    """
    if not operator_approved:
        raise PermissionError("Explicit operator approval required")
    if type(update_id) is not int or update_id < 0:
        raise ValueError("Invalid update ID")
    with sqlite3.connect(db_path, timeout=10) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS update_operator_audit ("
            "event_id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "update_id INTEGER NOT NULL, action TEXT NOT NULL, "
            "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        cursor = conn.execute(
            "UPDATE update_jobs SET state='pending',lease_until=0 "
            "WHERE update_id=? AND state='quarantined'", (update_id,),
        )
        if cursor.rowcount:
            conn.execute(
                "INSERT INTO update_operator_audit(update_id,action) VALUES (?,?)",
                (update_id, "release_quarantine"),
            )
        return cursor.rowcount == 1
