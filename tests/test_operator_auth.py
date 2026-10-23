import sqlite3
import pytest

from app.services.operator_auth import authorized_release
from app.services.update_jobs import enqueue, acquire, status
from app.services.update_quarantine import quarantine_if_exhausted


def test_operator_token_is_required_and_audited(tmp_path, monkeypatch):
    db = tmp_path / "jobs.sqlite"
    enqueue(db, 7)
    for n in range(3):
        assert acquire(db, 7, now=100 + 200 * n)
    assert quarantine_if_exhausted(db, 7)
    token = "a" * 48
    monkeypatch.delenv("YUGATNEO_OPERATOR_TOKEN", raising=False)
    with pytest.raises(PermissionError):
        authorized_release(db, 7, token)
    monkeypatch.setenv("YUGATNEO_OPERATOR_TOKEN", token)
    with pytest.raises(PermissionError):
        authorized_release(db, 7, "wrong")
    assert status(db, 7) == ("quarantined", 3)
    assert authorized_release(db, 7, token)
    assert status(db, 7) == ("pending", 3)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM update_operator_audit").fetchone()[0] == 1


def test_short_operator_secret_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("YUGATNEO_OPERATOR_TOKEN", "short")
    with pytest.raises(PermissionError):
        authorized_release(tmp_path / "jobs.sqlite", 1, "short")
