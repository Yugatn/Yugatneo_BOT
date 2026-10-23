"""Privacy-safe persistence regression tests across restarts and user boundaries."""
import sqlite3

import pytest
from cryptography.fernet import Fernet

from app.services.guided_report_storage import read_report, save_report
from app.services.personal_data import delete_telegram_user_records
from app.services.privacy_audit import audit_reflection_storage


def test_restart_readback_and_crypto_audit(tmp_path, monkeypatch):
    db = tmp_path / "persistent.sqlite"
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    save_report(db, "user-a", "Goal: practice drawing")
    # Reopen a fresh connection to simulate process restart.
    with sqlite3.connect(db) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert read_report(db, "user-a") == "Goal: practice drawing"
    assert audit_reflection_storage(db).passed


def test_two_users_can_update_independently_and_delete_one(tmp_path, monkeypatch):
    db = tmp_path / "two-users.sqlite"
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    save_report(db, "a", "First A")
    save_report(db, "b", "First B")
    save_report(db, "a", "Updated A")
    assert read_report(db, "a") == "Updated A"
    assert read_report(db, "b") == "First B"
    removed = delete_telegram_user_records(db, "a")
    assert removed["guided_reflection_reports"] == 1
    assert read_report(db, "a") is None
    assert read_report(db, "b") == "First B"


def test_wrong_key_cannot_decrypt_existing_report(tmp_path, monkeypatch):
    db = tmp_path / "key-rotation.sqlite"
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    save_report(db, "a", "Sensitive reflection")
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    with pytest.raises(Exception):
        read_report(db, "a")


def test_missing_key_refuses_to_save_even_after_restart(tmp_path, monkeypatch):
    db = tmp_path / "key-missing.sqlite"
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    save_report(db, "a", "Encrypted text")
    monkeypatch.delenv("YUGATNEO_DATA_ENCRYPTION_KEY", raising=False)
    with pytest.raises(RuntimeError):
        save_report(db, "b", "Never store plaintext")
    with sqlite3.connect(db) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM guided_reflection_reports WHERE telegram_user_id='b'"
        ).fetchone()[0] == 0
