from concurrent.futures import ThreadPoolExecutor
import sqlite3

from cryptography.fernet import Fernet

from app.services.idempotent_reflection import save_report_once
from app.services.guided_report_storage import read_report


def test_concurrent_replay_only_one_save(tmp_path, monkeypatch):
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    db = tmp_path / "concurrent.sqlite"
    def write(index):
        return save_report_once(db, "person", f"Report {index}", 1234)
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(write, range(12)))
    assert sum(outcomes) == 1
    assert read_report(db, "person").startswith("Report ")
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM reflection_save_receipts").fetchone()[0] == 1
