"""Atomic Fernet key rotation for opt-in guided reflection reports.

The old key and the new key are passed explicitly; no environment changes.
Any unreadable row aborts the entire transaction before modification.
Run only during a maintenance window with an independently verified backup.
"""
from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from cryptography.fernet import Fernet, InvalidToken

from app.services.diagnostic_encryption import PREFIX


@dataclass(frozen=True)
class RotationResult:
    examined: int
    rotated: int
    dry_run: bool


def rotate_guided_reports(db_path, *, old_key: str, new_key: str,
                          dry_run: bool = True) -> RotationResult:
    old_cipher = Fernet(old_key.encode("ascii"))
    new_cipher = Fernet(new_key.encode("ascii"))
    if old_key == new_key:
        raise ValueError("Old and new keys must differ")
    with sqlite3.connect(db_path, timeout=30) as conn:
        conn.execute("BEGIN IMMEDIATE")
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='guided_reflection_reports'"
        ).fetchone()
        if not exists:
            return RotationResult(0, 0, dry_run)
        rows = conn.execute(
            "SELECT telegram_user_id, encrypted_summary "
            "FROM guided_reflection_reports"
        ).fetchall()
        updates = []
        for user_id, encrypted in rows:
            if not encrypted.startswith(PREFIX):
                raise ValueError("Unencrypted reflection row blocks rotation")
            try:
                plain = old_cipher.decrypt(encrypted[len(PREFIX):].encode("ascii"))
            except (InvalidToken, ValueError, UnicodeError) as exc:
                raise ValueError("Unreadable reflection row blocks rotation") from exc
            if not dry_run:
                replacement = PREFIX + new_cipher.encrypt(plain).decode("ascii")
                updates.append((replacement, user_id))
        if dry_run:
            return RotationResult(len(rows), 0, True)
        conn.executemany(
            "UPDATE guided_reflection_reports SET encrypted_summary=?, "
            "updated_at=CURRENT_TIMESTAMP WHERE telegram_user_id=?",
            updates,
        )
        return RotationResult(len(rows), len(updates), False)
