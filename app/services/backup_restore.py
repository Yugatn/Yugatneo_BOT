"""Consistent SQLite backup and offline restore verification.

Backups may contain personal data; callers must secure the destination.
No database contents are printed or uploaded.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from app.services.backup_integrity import verify_sqlite_backup


@dataclass(frozen=True)
class BackupResult:
    verified: bool
    table_count: int


def create_verified_backup(source, destination) -> BackupResult:
    source_path = Path(source)
    target_path = Path(destination)
    if not source_path.is_file():
        raise FileNotFoundError("Source database missing")
    if source_path.resolve() == target_path.resolve():
        raise ValueError("Source and destination must differ")
    if target_path.exists():
        raise FileExistsError("Refusing to overwrite an existing backup")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(source_path.as_uri() + "?mode=ro", uri=True) as src:
            with sqlite3.connect(target_path) as dst:
                src.backup(dst)
        result = verify_sqlite_backup(target_path)
        if not result.passed:
            raise RuntimeError("Backup integrity verification failed")
        try:
            target_path.chmod(0o600)
        except OSError:
            pass
        return BackupResult(True, result.tables_checked)
    except BaseException:
        target_path.unlink(missing_ok=True)
        raise


def verify_restore_roundtrip(backup_path, restored_path) -> BackupResult:
    """Restore to a NEW offline path and verify structural integrity."""
    backup = Path(backup_path)
    target = Path(restored_path)
    if not verify_sqlite_backup(backup).passed:
        raise RuntimeError("Cannot restore from invalid backup")
    return create_verified_backup(backup, target)
