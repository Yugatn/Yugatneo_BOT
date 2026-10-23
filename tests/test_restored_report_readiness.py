from cryptography.fernet import Fernet

from app.services.backup_restore import create_verified_backup, verify_restore_roundtrip
from app.services.guided_report_storage import save_report
from app.services.report_readiness import count_unreadable_reports


def test_restored_backup_reports_are_readable(tmp_path, monkeypatch):
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    source = tmp_path / "source.sqlite"
    backup = tmp_path / "backup.sqlite"
    restored = tmp_path / "restored.sqlite"
    save_report(source, "test-user", "Test summary")
    assert create_verified_backup(source, backup).verified
    assert verify_restore_roundtrip(backup, restored).verified
    assert count_unreadable_reports(restored) == {"checked": 1, "unreadable": 0}


def test_restored_backup_rejects_wrong_key(tmp_path, monkeypatch):
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    source = tmp_path / "source.sqlite"
    backup = tmp_path / "backup.sqlite"
    restored = tmp_path / "restored.sqlite"
    save_report(source, "test-user", "Test summary")
    create_verified_backup(source, backup)
    verify_restore_roundtrip(backup, restored)
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    assert count_unreadable_reports(restored) == {"checked": 1, "unreadable": 1}
