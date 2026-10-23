from cryptography.fernet import Fernet
from app.services.guided_report_storage import save_report
from app.services.privacy_audit import audit_report_decryption


def test_report_audit(tmp_path, monkeypatch):
    db = tmp_path / "test.sqlite"
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    save_report(db, "example", "Sample")
    result = audit_report_decryption(db)
    assert result["checked"] == 1
    assert result["passed"]
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    assert not audit_report_decryption(db)["passed"]
