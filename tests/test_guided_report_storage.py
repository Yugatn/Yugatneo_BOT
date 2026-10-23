import sqlite3

import pytest
from cryptography.fernet import Fernet

from app.services.guided_report_storage import save_report, read_report
from app.services.personal_data import delete_telegram_user_records


def test_guided_report_encrypted_isolated_and_deletable(tmp_path, monkeypatch):
    db = tmp_path / "bot.sqlite"
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    save_report(db, "alice", "Private goal: drawing")
    save_report(db, "bob", "Private goal: music")
    with sqlite3.connect(db) as conn:
        stored = conn.execute(
            "SELECT encrypted_summary FROM guided_reflection_reports WHERE telegram_user_id='alice'"
        ).fetchone()[0]
    assert "drawing" not in stored
    assert read_report(db, "alice") == "Private goal: drawing"
    assert read_report(db, "bob") == "Private goal: music"
    delete_telegram_user_records(db, "alice")
    assert read_report(db, "alice") is None
    assert read_report(db, "bob") == "Private goal: music"


def test_guided_report_refuses_plaintext_storage(tmp_path, monkeypatch):
    monkeypatch.delenv("YUGATNEO_DATA_ENCRYPTION_KEY", raising=False)
    with pytest.raises(RuntimeError):
        save_report(tmp_path / "bot.sqlite", "alice", "Sensitive information")
