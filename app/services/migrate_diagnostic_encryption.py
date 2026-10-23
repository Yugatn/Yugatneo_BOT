"""Explicit one-time migration of legacy diagnostic answers to Fernet ciphertext.

Usage: python -m app.services.migrate_diagnostic_encryption --db PATH
Dry-run by default. Pass --apply to write. Ensure a secure encrypted backup
and verify the encryption key before applying.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

from app.services.diagnostic_encryption import (
    PREFIX, EncryptionConfigurationError, encrypt_diagnostic_json,
)
from app.services.sqlite_security import secure_sqlite_path


def migrate_diagnostic_answers(path: str | Path, *, apply: bool = False) -> dict[str, int]:
    key = os.environ.get("YUGATNEO_DATA_ENCRYPTION_KEY", "").strip()
    if not key:
        raise EncryptionConfigurationError("Encryption key required for migration")
    db = Path(path)
    if not db.is_file() or db.is_symlink():
        raise ValueError("Existing regular SQLite database required")
    secure_sqlite_path(db)
    counts = {"plaintext": 0, "encrypted": 0, "migrated": 0}
    with sqlite3.connect(db, timeout=10) as conn:
        conn.execute("BEGIN IMMEDIATE")
        table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='diagnostic_sessions'"
        ).fetchone()
        if not table:
            raise ValueError("diagnostic_sessions table not found")
        rows = conn.execute("SELECT subject_key, answers_json FROM diagnostic_sessions").fetchall()
        for subject, value in rows:
            if value.startswith(PREFIX):
                counts["encrypted"] += 1
                continue
            counts["plaintext"] += 1
            # Validate key even in dry-run; never output personal answers.
            encrypted = encrypt_diagnostic_json(value)
            if not encrypted.startswith(PREFIX):
                raise EncryptionConfigurationError("Encryption was not applied")
            if apply:
                conn.execute(
                    "UPDATE diagnostic_sessions SET answers_json=? WHERE subject_key=?",
                    (encrypted, subject),
                )
                counts["migrated"] += 1
        if not apply:
            conn.rollback()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Encrypt legacy diagnostic answers")
    parser.add_argument("--db", required=True, help="Existing SQLite file path")
    parser.add_argument("--apply", action="store_true", help="Commit migration (default: dry-run)")
    args = parser.parse_args()
    result = migrate_diagnostic_answers(args.db, apply=args.apply)
    print("Diagnostic migration counts (no personal content):", result)


if __name__ == "__main__":
    main()
