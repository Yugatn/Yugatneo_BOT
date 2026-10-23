"""Explicit allowlist for personal records in the Telegram SQLite database.

Do not delete content from unrelated tables or trust a user-supplied table name.
Deletion of external provider data, logs and backups requires separate handling.
"""
from __future__ import annotations

import sqlite3

PERSONAL_TABLES = (
    "wheel_scores",
    "wheel_score_history",
    "wheel_actions",
    "wheel_action_history",
    "career_reflection",
    "age_access",
    "bot_state",
    "dialogue_preferences",
    "user_language",
    "bot_security",
)


def delete_telegram_user_records(db_path, user_id: str) -> dict[str, int]:
    if not user_id:
        raise ValueError("Missing Telegram user ID")
    deleted: dict[str, int] = {}
    with sqlite3.connect(db_path, timeout=10) as conn:
        conn.execute("BEGIN IMMEDIATE")
        for table in PERSONAL_TABLES:
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            if not exists:
                continue
            # Table identifiers come exclusively from the static allowlist.
            cursor = conn.execute(
                f'DELETE FROM "{table}" WHERE telegram_user_id=?', (user_id,)
            )
            deleted[table] = cursor.rowcount
        for table in deleted:
            remaining = conn.execute(
                f'SELECT COUNT(*) FROM "{table}" WHERE telegram_user_id=?',
                (user_id,),
            ).fetchone()[0]
            if remaining:
                raise RuntimeError("Personal data deletion verification failed")
    return deleted
