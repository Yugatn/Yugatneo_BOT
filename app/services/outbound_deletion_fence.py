"""Short-lived privacy deletion fence for the experimental outbound ledger.

This table is operational suppression metadata, NOT an encrypted user report.
It retains one Telegram user identifier for at most 24 hours of *logical*
blocking; physical cleanup is lazy and must also be scheduled by operators.
The fence is never used for crisis responses or deletion acknowledgements.
"""
from __future__ import annotations

import sqlite3
import time

DELETION_FENCE_SECONDS = 24 * 60 * 60


def ensure_deletion_fence(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS outbound_deletion_fence ("
        "telegram_user_id TEXT PRIMARY KEY, "
        "expires_at INTEGER NOT NULL)"
    )


def record_deletion_fence(conn: sqlite3.Connection, user_id: str, *, now: int | None = None) -> None:
    """Call inside the SAME BEGIN IMMEDIATE transaction as scoped deletion."""
    if not isinstance(user_id, str) or not user_id:
        raise ValueError("Missing Telegram user ID")
    ensure_deletion_fence(conn)
    expires_at = (int(time.time()) if now is None else now) + DELETION_FENCE_SECONDS
    conn.execute(
        "INSERT INTO outbound_deletion_fence (telegram_user_id, expires_at) "
        "VALUES (?, ?) ON CONFLICT(telegram_user_id) DO UPDATE SET "
        "expires_at=MAX(outbound_deletion_fence.expires_at, excluded.expires_at)",
        (user_id, expires_at),
    )


def is_delivery_blocked(conn: sqlite3.Connection, user_id: str, *, now: int | None = None) -> bool:
    """Check inside the SAME BEGIN IMMEDIATE transaction as reservation."""
    ensure_deletion_fence(conn)
    current_time = int(time.time()) if now is None else now
    # Opportunistically purge this user's marker once its retention window
    # has ended, even if periodic maintenance has not yet run.
    conn.execute(
        "DELETE FROM outbound_deletion_fence "
        "WHERE telegram_user_id=? AND expires_at<=?",
        (user_id, current_time),
    )
    return conn.execute(
        "SELECT 1 FROM outbound_deletion_fence "
        "WHERE telegram_user_id=? AND expires_at>?",
        (user_id, current_time),
    ).fetchone() is not None


def is_user_deletion_fenced(db_path, user_id: str) -> bool:
    """Check the deletion barrier under the SQLite writer lock.

    Call before initiating an optional /start workflow so that a suppressed
    reply cannot still create a new preference or state record.
    """
    if not isinstance(user_id, str) or not user_id:
        raise ValueError("Missing Telegram user ID")
    with sqlite3.connect(db_path, timeout=10) as conn:
        conn.execute("BEGIN IMMEDIATE")
        return is_delivery_blocked(conn, user_id)


def purge_expired_deletion_fences(db_path, *, now: int | None = None) -> int:
    """Purge expired operational markers; can run offline or in maintenance."""
    current_time = int(time.time()) if now is None else now
    with sqlite3.connect(db_path, timeout=10) as conn:
        ensure_deletion_fence(conn)
        result = conn.execute(
            "DELETE FROM outbound_deletion_fence WHERE expires_at<=?",
            (current_time,),
        )
        return result.rowcount
