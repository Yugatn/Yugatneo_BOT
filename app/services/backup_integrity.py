"""Offline backup integrity checks; no user content is emitted."""
from __future__ import annotations

from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class BackupCheck:
    passed: bool
    integrity: str
    tables_checked: int


def verify_sqlite_backup(db_path) -> BackupCheck:
    """Open a backup read-only, verify SQLite integrity and known schema."""
    from pathlib import Path
    path = Path(db_path)
    if not path.is_file():
        return BackupCheck(False, "missing", 0)
    uri = path.resolve().as_uri() + "?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as conn:
            status = conn.execute("PRAGMA integrity_check").fetchone()[0]
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if "guided_reflection_reports" in tables:
                cols = {
                    row[1] for row in conn.execute(
                        "PRAGMA table_info(guided_reflection_reports)"
                    )
                }
                schema_ok = {"telegram_user_id", "encrypted_summary"}.issubset(cols)
            else:
                schema_ok = True
            return BackupCheck(status == "ok" and schema_ok,
                               "ok" if status == "ok" else "failed",
                               len(tables))
    except sqlite3.DatabaseError:
        return BackupCheck(False, "unreadable", 0)
