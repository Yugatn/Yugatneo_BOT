"""Operational metrics for the Telegram update queue."""
import sqlite3


def update_metrics(db_path):
    with sqlite3.connect(db_path) as conn:
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='update_jobs'").fetchone()
        if not exists:
            return {"total": 0, "states": {}}
        states = dict(conn.execute("SELECT state, COUNT(*) FROM update_jobs GROUP BY state"))
        return {"total": sum(states.values()), "states": states}


def release_quarantined(db_path, update_id):
    if type(update_id) is not int or update_id < 0:
        raise ValueError("Invalid update ID")
    with sqlite3.connect(db_path, timeout=10) as conn:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute(
            "UPDATE update_jobs SET state='pending',lease_until=0 "
            "WHERE update_id=? AND state='quarantined'", (update_id,),
        )
        return cursor.rowcount == 1
