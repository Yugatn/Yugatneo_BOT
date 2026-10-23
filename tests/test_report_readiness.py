import pytest
from cryptography.fernet import Fernet

from app.services.guided_report_storage import save_report
from app.services.report_readiness import count_unreadable_reports


def test_report_readiness_with_matching_key(tmp_path, monkeypatch):
    db = tmp_path / "test.sqlite"
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", key)
    save_report(db, "user", "Example")
    assert count_unreadable_reports(db) == {"checked": 1, "unreadable": 0}


def test_report_readiness_with_different_key(tmp_path, monkeypatch):
    db = tmp_path / "test.sqlite"
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    save_report(db, "user", "Example")
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    assert count_unreadable_reports(db) == {"checked": 1, "unreadable": 1}


def test_report_readiness_empty_database(tmp_path):
    assert count_unreadable_reports(tmp_path / "empty.sqlite") == {
        "checked": 0, "unreadable": 0
    }
