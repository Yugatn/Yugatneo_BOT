import sqlite3
import threading

from app.services.backup_restore import create_verified_backup
from app.services.backup_integrity import verify_sqlite_backup


def test_backup_during_concurrent_committed_writes(tmp_path):
    source = tmp_path / "active.sqlite"
    destination = tmp_path / "snapshot.sqlite"
    with sqlite3.connect(source) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE events (n INTEGER PRIMARY KEY)")
    started = threading.Event()
    errors = []

    def writer():
        try:
            with sqlite3.connect(source, timeout=10) as conn:
                for n in range(60):
                    conn.execute("INSERT INTO events(n) VALUES (?)", (n,))
                    conn.commit()
                    if n == 4:
                        started.set()
        except Exception as exc:
            errors.append(exc)
            started.set()

    thread = threading.Thread(target=writer)
    thread.start()
    assert started.wait(timeout=10)
    snapshot = create_verified_backup(source, destination)
    thread.join(timeout=10)
    assert not thread.is_alive()
    assert not errors
    assert snapshot.verified
    with sqlite3.connect(destination) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        assert 0 <= count <= 60


def test_integrity_reports_invalid_schema(tmp_path):
    source = tmp_path / "invalid.sqlite"
    with sqlite3.connect(source) as conn:
        conn.execute(
            "CREATE TABLE guided_reflection_reports (telegram_user_id TEXT)"
        )
    result = verify_sqlite_backup(source)
    assert not result.passed
    assert result.integrity == "invalid_schema"
