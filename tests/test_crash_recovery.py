"""SQLite crash-recovery regression tests for offline CI."""
import sqlite3
import subprocess
import sys

from cryptography.fernet import Fernet

from app.services.backup_restore import create_verified_backup, verify_restore_roundtrip
from app.services.guided_report_storage import read_report, save_report


def test_aborted_child_transaction_does_not_commit(tmp_path):
    db = tmp_path / "crash.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE items (value TEXT)")
        conn.execute("INSERT INTO items VALUES ('committed')")
    script = (
        "import os,sqlite3,sys;"
        "c=sqlite3.connect(sys.argv[1]);"
        "c.execute('BEGIN IMMEDIATE');"
        "c.execute('INSERT INTO items VALUES (?)',('uncommitted',));"
        "os._exit(7)"
    )
    child = subprocess.run([sys.executable, "-c", script, str(db)],
                           capture_output=True, timeout=10, check=False)
    assert child.returncode == 7
    with sqlite3.connect(db) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("SELECT value FROM items").fetchall() == [("committed",)]


def test_encrypted_report_survives_backup_and_restore(tmp_path, monkeypatch):
    original = tmp_path / "source.sqlite"
    backup = tmp_path / "backup.sqlite"
    restored = tmp_path / "restored.sqlite"
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    save_report(original, "a", "Private progress note")
    assert create_verified_backup(original, backup).verified
    assert verify_restore_roundtrip(backup, restored).verified
    assert read_report(restored, "a") == "Private progress note"
