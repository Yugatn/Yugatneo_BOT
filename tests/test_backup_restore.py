import sqlite3

import pytest

from app.services.backup_restore import create_verified_backup, verify_restore_roundtrip


def test_backup_restore_preserves_rows(tmp_path):
    original = tmp_path / "original.sqlite"
    backup = tmp_path / "backup.sqlite"
    restored = tmp_path / "restored.sqlite"
    with sqlite3.connect(original) as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, note TEXT)")
        conn.execute("INSERT INTO sample(note) VALUES (?)", ("Example",))
    result = create_verified_backup(original, backup)
    assert result.verified and result.table_count >= 1
    restored_result = verify_restore_roundtrip(backup, restored)
    assert restored_result.verified
    with sqlite3.connect(restored) as conn:
        assert conn.execute("SELECT note FROM sample").fetchone()[0] == "Example"


def test_backup_refuses_to_overwrite_existing_file(tmp_path):
    original = tmp_path / "original.sqlite"
    destination = tmp_path / "existing.sqlite"
    with sqlite3.connect(original) as conn:
        conn.execute("CREATE TABLE example (id INTEGER)")
    destination.write_text("do not overwrite")
    with pytest.raises(FileExistsError):
        create_verified_backup(original, destination)
    assert destination.read_text() == "do not overwrite"


def test_backup_refuses_missing_source(tmp_path):
    with pytest.raises(FileNotFoundError):
        create_verified_backup(tmp_path / "missing.sqlite", tmp_path / "backup.sqlite")


def test_backup_refuses_same_path(tmp_path):
    db = tmp_path / "same.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE example (id INTEGER)")
    with pytest.raises(ValueError):
        create_verified_backup(db, db)
