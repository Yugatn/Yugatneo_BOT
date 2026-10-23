"""Durable update lifecycle: pending, processing lease, and completion.

No raw message content is stored. Retrying an expired lease can repeat
side effects; callers must separately make writes idempotent.
"""
from __future__ import annotations

import sqlite3
import time


def _init(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS update_jobs ("
        "update_id INTEGER PRIMARY KEY, state TEXT NOT NULL, "
        "lease_until INTEGER NOT NULL DEFAULT 0, attempts INTEGER NOT NULL DEFAULT 0)"
    )


def enqueue(db_path, update_id: int) -> None:
    if type(update_id) is not int or update_id < 0:
        raise ValueError("Invalid update ID")
    with sqlite3.connect(db_path, timeout=10) as conn:
        _init(conn)
        conn.execute(
            "INSERT OR IGNORE INTO update_jobs(update_id,state) VALUES (?,'pending')",
            (update_id,),
        )


def acquire(db_path, update_id: int, *, now: int | None = None,
            lease_seconds: int = 120) -> bool:
    if lease_seconds <= 0:
        raise ValueError("Lease must be positive")
    timestamp = int(time.time()) if now is None else now
    with sqlite3.connect(db_path, timeout=10) as conn:
        _init(conn)
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute(
            "UPDATE update_jobs SET state='processing', lease_until=?, "
            "attempts=attempts+1 WHERE update_id=? AND "
            "(state='pending' OR (state='processing' AND lease_until<=?))",
            (timestamp + lease_seconds, update_id, timestamp),
        )
        return cursor.rowcount == 1


def complete(db_path, update_id: int) -> None:
    with sqlite3.connect(db_path, timeout=10) as conn:
        _init(conn)
        conn.execute(
            "UPDATE update_jobs SET state='done', lease_until=0 "
            "WHERE update_id=? AND state='processing'", (update_id,),
        )


def status(db_path, update_id: int) -> tuple[str, int] | None:
    with sqlite3.connect(db_path, timeout=10) as conn:
        _init(conn)
        row = conn.execute(
            "SELECT state, attempts FROM update_jobs WHERE update_id=?",
            (update_id,),
        ).fetchone()
        return (row[0], row[1]) if row else None
