"""Explicit allowlist for personal records in the Telegram SQLite database.

Do not delete content from unrelated tables or trust a user-supplied table name.
Deletion of external provider data, logs and backups requires separate handling.
"""
from __future__ import annotations

import sqlite3

from app.services.outbound_deletion_fence import record_deletion_fence

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
    "guided_reflection_reports",
    "reflection_save_receipts",
    "user_outbound_delivery",
)

# Literal SQL statements: table identifiers cannot come from user input.
_TABLE_SQL = {
    "wheel_scores": (
        'DELETE FROM "wheel_scores" WHERE telegram_user_id=?',
        'SELECT COUNT(*) FROM "wheel_scores" WHERE telegram_user_id=?',
    ),
    "wheel_score_history": (
        'DELETE FROM "wheel_score_history" WHERE telegram_user_id=?',
        'SELECT COUNT(*) FROM "wheel_score_history" WHERE telegram_user_id=?',
    ),
    "wheel_actions": (
        'DELETE FROM "wheel_actions" WHERE telegram_user_id=?',
        'SELECT COUNT(*) FROM "wheel_actions" WHERE telegram_user_id=?',
    ),
    "wheel_action_history": (
        'DELETE FROM "wheel_action_history" WHERE telegram_user_id=?',
        'SELECT COUNT(*) FROM "wheel_action_history" WHERE telegram_user_id=?',
    ),
    "career_reflection": (
        'DELETE FROM "career_reflection" WHERE telegram_user_id=?',
        'SELECT COUNT(*) FROM "career_reflection" WHERE telegram_user_id=?',
    ),
    "age_access": (
        'DELETE FROM "age_access" WHERE telegram_user_id=?',
        'SELECT COUNT(*) FROM "age_access" WHERE telegram_user_id=?',
    ),
    "bot_state": (
        'DELETE FROM "bot_state" WHERE telegram_user_id=?',
        'SELECT COUNT(*) FROM "bot_state" WHERE telegram_user_id=?',
    ),
    "dialogue_preferences": (
        'DELETE FROM "dialogue_preferences" WHERE telegram_user_id=?',
        'SELECT COUNT(*) FROM "dialogue_preferences" WHERE telegram_user_id=?',
    ),
    "user_language": (
        'DELETE FROM "user_language" WHERE telegram_user_id=?',
        'SELECT COUNT(*) FROM "user_language" WHERE telegram_user_id=?',
    ),
    "bot_security": (
        'DELETE FROM "bot_security" WHERE telegram_user_id=?',
        'SELECT COUNT(*) FROM "bot_security" WHERE telegram_user_id=?',
    ),
    "guided_reflection_reports": (
        'DELETE FROM "guided_reflection_reports" WHERE telegram_user_id=?',
        'SELECT COUNT(*) FROM "guided_reflection_reports" WHERE telegram_user_id=?',
    ),
    "reflection_save_receipts": (
        'DELETE FROM "reflection_save_receipts" WHERE telegram_user_id=?',
        'SELECT COUNT(*) FROM "reflection_save_receipts" WHERE telegram_user_id=?',
    ),
    "user_outbound_delivery": (
        'DELETE FROM "user_outbound_delivery" WHERE telegram_user_id=?',
        'SELECT COUNT(*) FROM "user_outbound_delivery" WHERE telegram_user_id=?',
    ),
}


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
            delete_sql, _ = _TABLE_SQL[table]
            cursor = conn.execute(delete_sql, (user_id,))
            deleted[table] = cursor.rowcount
        for table in deleted:
            _, count_sql = _TABLE_SQL[table]
            remaining = conn.execute(count_sql, (user_id,)).fetchone()[0]
            if remaining:
                raise RuntimeError("Personal data deletion verification failed")
        # Commit this bounded suppression marker atomically with deletion.
        # It is separate operational metadata, not a retained report.
        record_deletion_fence(conn, user_id)
    return deleted
