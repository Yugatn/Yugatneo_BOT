import sqlite3

from app.services.backup_integrity import verify_sqlite_backup
from app.services.guided_report_storage import ensure_table


def test_backup_integrity_passes_for_valid_database(tmp_path):
    db = tmp_path / "backup.sqlite"
    with sqlite3.connect(db) as conn:
        ensure_table(conn)
    result = verify_sqlite_backup(db)
    assert result.passed
    assert result.integrity == "ok"
    assert result.tables_checked >= 1


def test_backup_integrity_rejects_missing_database(tmp_path):
    result = verify_sqlite_backup(tmp_path / "missing.sqlite")
    assert not result.passed
    assert result.integrity == "missing"


def test_backup_integrity_rejects_invalid_bytes(tmp_path):
    db = tmp_path / "broken.sqlite"
    db.write_bytes(b"not a database")
    result = verify_sqlite_backup(db)
    assert not result.passed
    assert result.integrity == "unreadable"
