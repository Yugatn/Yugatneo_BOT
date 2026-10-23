"""Idempotent encrypted reflection saves keyed by Telegram update ID.

The receipt and report write share one SQLite transaction.
"""
import sqlite3

from app.services.diagnostic_encryption import (
    PREFIX, EncryptionConfigurationError, encrypt_diagnostic_json,
)
from app.services.guided_report_storage import ensure_table


def save_report_once(db_path, user_id: str, report: str, update_id: int) -> bool:
    if not user_id or not report or type(update_id) is not int or update_id < 0:
        raise ValueError("Valid user, report and update ID required")
    with sqlite3.connect(db_path, timeout=10) as conn:
        ensure_table(conn)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS reflection_save_receipts "
            "(telegram_user_id TEXT NOT NULL, update_id INTEGER NOT NULL, "
            "PRIMARY KEY(telegram_user_id, update_id))"
        )
        conn.execute("BEGIN IMMEDIATE")
        receipt = conn.execute(
            "INSERT OR IGNORE INTO reflection_save_receipts "
            "(telegram_user_id,update_id) VALUES (?,?)", (user_id, update_id),
        )
        if receipt.rowcount == 0:
            return False
        encrypted = encrypt_diagnostic_json(report)
        if not encrypted.startswith(PREFIX):
            raise EncryptionConfigurationError("Encryption key required")
        conn.execute(
            "INSERT INTO guided_reflection_reports(telegram_user_id,encrypted_summary) "
            "VALUES (?,?) ON CONFLICT(telegram_user_id) DO UPDATE SET "
            "encrypted_summary=excluded.encrypted_summary,updated_at=CURRENT_TIMESTAMP",
            (user_id, encrypted),
        )
        return True
