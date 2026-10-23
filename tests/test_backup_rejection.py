import sqlite3

from app.services.backup_integrity import verify_sqlite_backup


def test_integrity_rejects_non_sqlite_file(tmp_path):
    path = tmp_path / "invalid.sqlite"
    path.write_bytes(b"not a sqlite database")
    result = verify_sqlite_backup(path)
    assert not result.passed
    assert result.integrity == "unreadable"


def test_integrity_rejects_incomplete_reflection_schema(tmp_path):
    path = tmp_path / "schema.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE guided_reflection_reports (telegram_user_id TEXT)")
    result = verify_sqlite_backup(path)
    assert not result.passed
    assert result.integrity == "invalid_schema"
