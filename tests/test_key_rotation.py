from cryptography.fernet import Fernet
import pytest

from app.services.guided_report_storage import save_report, read_report
from app.services.key_rotation import rotate_guided_reports


def test_rotation_dry_run_and_commit(tmp_path, monkeypatch):
    old = Fernet.generate_key().decode()
    new = Fernet.generate_key().decode()
    db = tmp_path / "rotate.sqlite"
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", old)
    save_report(db, "alice", "Private goal")
    preview = rotate_guided_reports(db, old_key=old, new_key=new)
    assert preview.examined == 1 and preview.rotated == 0
    assert read_report(db, "alice") == "Private goal"
    result = rotate_guided_reports(db, old_key=old, new_key=new, dry_run=False)
    assert result.rotated == 1
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", new)
    assert read_report(db, "alice") == "Private goal"


def test_wrong_old_key_refuses_rotation(tmp_path, monkeypatch):
    original = Fernet.generate_key().decode()
    db = tmp_path / "rotate.sqlite"
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", original)
    save_report(db, "alice", "Private goal")
    with pytest.raises(ValueError):
        rotate_guided_reports(
            db,
            old_key=Fernet.generate_key().decode(),
            new_key=Fernet.generate_key().decode(),
            dry_run=False,
        )
    assert read_report(db, "alice") == "Private goal"
