"""Persistent replay protection for Telegram update IDs.

Record update IDs in SQLite, not process memory, to survive restarts.
Call after validating the update envelope. This provides at-most-once
processing attempts, not guaranteed delivery if a process crashes mid-handler.
"""
from __future__ import annotations

import sqlite3
import time


def claim_update(db_path, update_id: int, *, now: int | None = None) -> bool:
    if not isinstance(update_id, int) or isinstance(update_id, bool) or update_id < 0:
        raise ValueError("Invalid Telegram update ID")
    timestamp = int(time.time()) if now is None else now
    with sqlite3.connect(db_path, timeout=10) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS processed_updates "
            "(update_id INTEGER PRIMARY KEY, claimed_at INTEGER NOT NULL)"
        )
        conn.execute("BEGIN IMMEDIATE")
        result = conn.execute(
            "INSERT OR IGNORE INTO processed_updates(update_id, claimed_at) "
            "VALUES (?, ?)", (update_id, timestamp),
        )
        return result.rowcount == 1


def prune_updates(db_path, *, before: int) -> int:
    with sqlite3.connect(db_path, timeout=10) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS processed_updates "
            "(update_id INTEGER PRIMARY KEY, claimed_at INTEGER NOT NULL)"
        )
        result = conn.execute(
            "DELETE FROM processed_updates WHERE claimed_at < ?", (before,)
        )
        return result.rowcount
