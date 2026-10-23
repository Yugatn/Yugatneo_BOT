"""Concurrency regression tests for independent encrypted user reports."""
from concurrent.futures import ThreadPoolExecutor

from cryptography.fernet import Fernet

from app.services.guided_report_storage import save_report, read_report


def test_parallel_users_keep_independent_reports(tmp_path, monkeypatch):
    db = tmp_path / "parallel.sqlite"
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    users = [(f"user-{n}", f"Report {n}") for n in range(8)]

    def write(item):
        user_id, report = item
        save_report(db, user_id, report)

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(write, users))

    for user_id, expected in users:
        assert read_report(db, user_id) == expected
