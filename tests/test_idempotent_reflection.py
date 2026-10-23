from cryptography.fernet import Fernet
import pytest

from app.services.idempotent_reflection import save_report_once
from app.services.guided_report_storage import read_report


def test_same_update_cannot_overwrite_reflection_twice(tmp_path, monkeypatch):
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    db = tmp_path / "bot.sqlite"
    assert save_report_once(db, "person1", "First result", 100)
    assert not save_report_once(db, "person1", "Changed result", 100)
    assert read_report(db, "person1") == "First result"
    assert save_report_once(db, "person1", "New result", 101)
    assert read_report(db, "person1") == "New result"


def test_users_have_independent_receipts(tmp_path, monkeypatch):
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    db = tmp_path / "bot.sqlite"
    assert save_report_once(db, "a", "Report A", 10)
    assert save_report_once(db, "b", "Report B", 10)
    assert read_report(db, "a") == "Report A"
    assert read_report(db, "b") == "Report B"


def test_failed_encryption_rolls_back_receipt(tmp_path, monkeypatch):
    monkeypatch.delenv("YUGATNEO_DATA_ENCRYPTION_KEY", raising=False)
    db = tmp_path / "bot.sqlite"
    with pytest.raises(Exception):
        save_report_once(db, "a", "Sensitive result", 10)
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    assert save_report_once(db, "a", "Sensitive result", 10)
