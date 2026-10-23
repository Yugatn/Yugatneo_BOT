import sqlite3

import pytest
from cryptography.fernet import Fernet

from app.services.diagnostic_encryption import PREFIX, decrypt_diagnostic_json, encrypt_diagnostic_json
from app.services.migrate_career_encryption import migrate_career_reflections


def setup_db(path):
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE career_reflection("
            "telegram_user_id TEXT PRIMARY KEY, interest TEXT NOT NULL, "
            "skill TEXT NOT NULL, next_experiment TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO career_reflection VALUES (?,?,?,?)",
            ("u1", "Games", "Drawing", "Build a demo"),
        )


def test_career_migration_dry_run_apply_idempotent(tmp_path, monkeypatch):
    db = tmp_path / "bot.sqlite3"
    setup_db(db)
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    assert migrate_career_reflections(db) == {
        "plaintext_fields": 3, "encrypted_fields": 0, "migrated_fields": 0
    }
    with sqlite3.connect(db) as conn:
        assert conn.execute(
            "SELECT interest FROM career_reflection"
        ).fetchone()[0] == "Games"
    assert migrate_career_reflections(db, apply=True)["migrated_fields"] == 3
    with sqlite3.connect(db) as conn:
        fields = conn.execute(
            "SELECT interest, skill, next_experiment FROM career_reflection"
        ).fetchone()
    assert all(value.startswith(PREFIX) for value in fields)
    assert [decrypt_diagnostic_json(value) for value in fields] == [
        "Games", "Drawing", "Build a demo"
    ]
    assert migrate_career_reflections(db, apply=True)["migrated_fields"] == 0


def test_mixed_plaintext_and_encrypted_fields(tmp_path, monkeypatch):
    db = tmp_path / "bot.sqlite3"
    setup_db(db)
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE career_reflection SET interest=?",
            (encrypt_diagnostic_json("Games"),),
        )
    assert migrate_career_reflections(db, apply=True) == {
        "plaintext_fields": 2, "encrypted_fields": 1, "migrated_fields": 2
    }


def test_missing_key_and_missing_file(tmp_path, monkeypatch):
    db = tmp_path / "bot.sqlite3"
    setup_db(db)
    monkeypatch.delenv("YUGATNEO_DATA_ENCRYPTION_KEY", raising=False)
    with pytest.raises(Exception, match="Encryption key required"):
        migrate_career_reflections(db, apply=True)
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    with pytest.raises(ValueError):
        migrate_career_reflections(tmp_path / "absent.sqlite3")
