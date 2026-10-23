"""Bounded retry decisions for failed Telegram update jobs.

After repeated failures, stop automatic processing and require operator
review. This prevents a single malformed update from blocking polling forever.
"""
import sqlite3

MAX_ATTEMPTS = 3


def quarantine_if_exhausted(db_path, update_id, max_attempts=MAX_ATTEMPTS):
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    with sqlite3.connect(db_path, timeout=10) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT state,attempts FROM update_jobs WHERE update_id=?",
            (update_id,),
        ).fetchone()
        if row is None or row[0] == "done" or row[1] < max_attempts:
            return False
        changed = conn.execute(
            "UPDATE update_jobs SET state='quarantined',lease_until=0 "
            "WHERE update_id=? AND state='processing'", (update_id,),
        )
        return changed.rowcount == 1
