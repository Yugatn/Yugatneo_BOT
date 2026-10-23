import sqlite3

from cryptography.fernet import Fernet

from app.services.backup_restore import create_verified_backup, verify_restore_roundtrip
from app.services.guided_report_storage import read_report
from app.services.idempotent_reflection import save_report_once
from app.services.personal_data import delete_telegram_user_records


def test_deletion_after_backup_restore_clears_report_and_receipts(tmp_path, monkeypatch):
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    source = tmp_path / "source.sqlite"
    backup = tmp_path / "backup.sqlite"
    restored = tmp_path / "restored.sqlite"
    assert save_report_once(source, "user-a", "Private reflection", 11)
    assert save_report_once(source, "user-b", "Another reflection", 12)
    create_verified_backup(source, backup)
    verify_restore_roundtrip(backup, restored)
    result = delete_telegram_user_records(restored, "user-a")
    assert result["guided_reflection_reports"] == 1
    assert result["reflection_save_receipts"] == 1
    assert read_report(restored, "user-a") is None
    assert read_report(restored, "user-b") == "Another reflection"
    with sqlite3.connect(restored) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM reflection_save_receipts WHERE telegram_user_id=?",
            ("user-a",),
        ).fetchone()[0] == 0
