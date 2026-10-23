import sqlite3

from app.services.privacy_audit import audit_reflection_storage
from app.services.guided_report_storage import ensure_table


def test_empty_database_is_safe_without_creating_records(tmp_path):
    path = tmp_path / "empty.sqlite"
    report = audit_reflection_storage(path)
    assert report.passed
    assert report.checked_tables == 0


def test_plaintext_is_flagged_without_exposing_content(tmp_path):
    path = tmp_path / "test.sqlite"
    with sqlite3.connect(path) as conn:
        ensure_table(conn)
        conn.execute(
            "INSERT INTO guided_reflection_reports "
            "(telegram_user_id, encrypted_summary) VALUES (?, ?)",
            ("private-user-123", "my secret thoughts"),
        )
    report = audit_reflection_storage(path)
    assert not report.passed
    assert "unencrypted_reflection_detected" in report.findings
    assert "my secret thoughts" not in str(report)
    assert "private-user-123" not in str(report)


def test_encrypted_prefix_passes_structural_audit(tmp_path):
    path = tmp_path / "test.sqlite"
    with sqlite3.connect(path) as conn:
        ensure_table(conn)
        conn.execute(
            "INSERT INTO guided_reflection_reports "
            "(telegram_user_id, encrypted_summary) VALUES (?, ?)",
            ("user-1", "fernet:v1:placeholder"),
        )
    report = audit_reflection_storage(path)
    assert report.passed
    assert report.checked_tables == 1
