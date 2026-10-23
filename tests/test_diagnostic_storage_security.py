"""Ensure sensitive diagnostic SQLite storage uses private filesystem permissions."""
import os
import sqlite3

import pytest

from app.services import diagnostic_flow
from app.services.sqlite_security import is_private_file


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions only")
def test_diagnostic_database_permissions(tmp_path, monkeypatch):
    path = tmp_path / "diagnostic.sqlite3"
    monkeypatch.setattr(diagnostic_flow, "_db_path", lambda: str(path))
    with diagnostic_flow._connect() as conn:
        conn.execute("SELECT COUNT(*) FROM diagnostic_sessions")
    assert is_private_file(path)


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions only")
def test_diagnostic_deletion_does_not_touch_other_user(tmp_path, monkeypatch):
    path = tmp_path / "diagnostic.sqlite3"
    monkeypatch.setattr(diagnostic_flow, "_db_path", lambda: str(path))
    diagnostic_flow._write("telegram", "user-1", 0, {"goal": "general"})
    diagnostic_flow._write("telegram", "user-2", 0, {"goal": "work"})
    diagnostic_flow.clear_diagnostic("telegram", "user-1")
    assert diagnostic_flow._read("telegram", "user-1") is None
    assert diagnostic_flow._read("telegram", "user-2") is not None
    assert is_private_file(path)
