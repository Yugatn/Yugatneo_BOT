import sqlite3

import pytest
from cryptography.fernet import Fernet

from app.services.diagnostic_encryption import PREFIX, decrypt_diagnostic_json, EncryptionConfigurationError
from app.services.migrate_diagnostic_encryption import migrate_diagnostic_answers


def make_db(path):
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE diagnostic_sessions(subject_key TEXT PRIMARY KEY, answers_json TEXT)")
        conn.executemany("INSERT INTO diagnostic_sessions VALUES (?,?)", [
            ("a", '{"goal":"private"}'), ("b", '{"goal":"creative"}')
        ])


def test_migration_dry_run_then_apply_and_idempotency(tmp_path, monkeypatch):
    db = tmp_path / "diagnostic.sqlite3"
    make_db(db)
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    result = migrate_diagnostic_answers(db)
    assert result == {"plaintext": 2, "encrypted": 0, "migrated": 0}
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT answers_json FROM diagnostic_sessions WHERE subject_key='a'").fetchone()[0] == '{"goal":"private"}'
    result = migrate_diagnostic_answers(db, apply=True)
    assert result["migrated"] == 2
    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT answers_json FROM diagnostic_sessions").fetchall()
    assert all(value.startswith(PREFIX) for (value,) in rows)
    assert decrypt_diagnostic_json(rows[0][0]) == '{"goal":"private"}'
    assert migrate_diagnostic_answers(db, apply=True)["migrated"] == 0


def test_migration_requires_key(tmp_path, monkeypatch):
    db = tmp_path / "diagnostic.sqlite3"
    make_db(db)
    monkeypatch.delenv("YUGATNEO_DATA_ENCRYPTION_KEY", raising=False)
    with pytest.raises(EncryptionConfigurationError):
        migrate_diagnostic_answers(db, apply=True)


def test_migration_rejects_missing_database(tmp_path, monkeypatch):
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    with pytest.raises(ValueError):
        migrate_diagnostic_answers(tmp_path / "missing.sqlite3")
