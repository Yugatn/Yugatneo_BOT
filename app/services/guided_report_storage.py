"""Explicit opt-in storage for completed guided-reflection summaries.

Only encrypted summaries are accepted; never persist raw question responses.
"""
from __future__ import annotations

import sqlite3

from app.services.diagnostic_encryption import (
    PREFIX, EncryptionConfigurationError, encrypt_diagnostic_json,
    decrypt_diagnostic_json,
)


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS guided_reflection_reports (
            telegram_user_id TEXT PRIMARY KEY,
            encrypted_summary TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)


def save_report(db_path, user_id: str, report: str) -> None:
    if not user_id or not report:
        raise ValueError("User ID and report required")
    encrypted = encrypt_diagnostic_json(report)
    if not encrypted.startswith(PREFIX):
        raise EncryptionConfigurationError(
            "Encryption key is required to save personal reflection"
        )
    with sqlite3.connect(db_path) as conn:
        ensure_table(conn)
        conn.execute(
            "INSERT INTO guided_reflection_reports(telegram_user_id, encrypted_summary) "
            "VALUES (?, ?) ON CONFLICT(telegram_user_id) DO UPDATE SET "
            "encrypted_summary=excluded.encrypted_summary, updated_at=CURRENT_TIMESTAMP",
            (user_id, encrypted),
        )


def read_report(db_path, user_id: str) -> str | None:
    with sqlite3.connect(db_path) as conn:
        ensure_table(conn)
        row = conn.execute(
            "SELECT encrypted_summary FROM guided_reflection_reports "
            "WHERE telegram_user_id=?", (user_id,),
        ).fetchone()
    return decrypt_diagnostic_json(row[0]) if row else None
