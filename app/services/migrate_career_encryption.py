"""Dry-run-first migration of legacy career reflection fields to Fernet.

Stop the bot and create a verified encrypted backup before --apply.
This tool does not migrate wheel or diagnostic tables.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

from app.services.diagnostic_encryption import (
    PREFIX, EncryptionConfigurationError, encrypt_diagnostic_json,
    decrypt_diagnostic_json,
)
from app.services.sqlite_security import secure_sqlite_path

FIELDS = ("interest", "skill", "next_experiment")


def migrate_career_reflections(path: str | Path, *, apply: bool = False) -> dict[str, int]:
    if not os.environ.get("YUGATNEO_DATA_ENCRYPTION_KEY", "").strip():
        raise EncryptionConfigurationError("Encryption key required for migration")
    db = Path(path)
    if db.is_symlink() or not db.is_file():
        raise ValueError("Existing regular SQLite database required")
    secure_sqlite_path(db)
    counts = {"plaintext_fields": 0, "encrypted_fields": 0, "migrated_fields": 0}
    with sqlite3.connect(db, timeout=10) as conn:
        conn.execute("BEGIN IMMEDIATE")
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='career_reflection'"
        ).fetchone()
        if not exists:
            raise ValueError("career_reflection table not found")
        rows = conn.execute(
            "SELECT telegram_user_id, interest, skill, next_experiment FROM career_reflection"
        ).fetchall()
        for user_id, *values in rows:
            updated = list(values)
            changed = False
            for index, value in enumerate(values):
                if value.startswith(PREFIX):
                    # Verify current key can decrypt before modifying any row.
                    decrypt_diagnostic_json(value)
                    counts["encrypted_fields"] += 1
                else:
                    updated[index] = encrypt_diagnostic_json(value)
                    if not updated[index].startswith(PREFIX):
                        raise EncryptionConfigurationError("Encryption was not applied")
                    counts["plaintext_fields"] += 1
                    changed = True
            if apply and changed:
                conn.execute(
                    "UPDATE career_reflection SET interest=?, skill=?, next_experiment=? "
                    "WHERE telegram_user_id=?",
                    (*updated, user_id),
                )
                counts["migrated_fields"] += sum(
                    not value.startswith(PREFIX) for value in values
                )
        if not apply:
            conn.rollback()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Encrypt legacy career reflections")
    parser.add_argument("--db", required=True, help="Existing SQLite file")
    parser.add_argument("--apply", action="store_true", help="Commit changes; default is dry-run")
    args = parser.parse_args()
    print("Career migration counts (no personal content):",
          migrate_career_reflections(args.db, apply=args.apply))


if __name__ == "__main__":
    main()
