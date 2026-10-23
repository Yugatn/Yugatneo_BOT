import sqlite3

import pytest

from app.services.personal_data import delete_telegram_user_records, PERSONAL_TABLES


def test_deletion_is_scoped_to_one_telegram_user(tmp_path):
    path = tmp_path / "user.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE wheel_scores(telegram_user_id TEXT, sphere TEXT)")
        conn.execute("CREATE TABLE bot_security(telegram_user_id TEXT, verified INTEGER)")
        conn.execute("CREATE TABLE parenting_knowledge(key TEXT)")
        conn.executemany(
            "INSERT INTO wheel_scores VALUES (?,?)",
            [("alice", "health"), ("bob", "creativity")],
        )
        conn.executemany(
            "INSERT INTO bot_security VALUES (?,?)", [("alice", 1), ("bob", 1)]
        )
        conn.execute("INSERT INTO parenting_knowledge VALUES ('creativity')")
    result = delete_telegram_user_records(path, "alice")
    assert result["wheel_scores"] == 1
    assert result["bot_security"] == 1
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM wheel_scores WHERE telegram_user_id='alice'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM wheel_scores WHERE telegram_user_id='bob'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM parenting_knowledge").fetchone()[0] == 1


def test_empty_user_id_rejected(tmp_path):
    with pytest.raises(ValueError):
        delete_telegram_user_records(tmp_path / "test.sqlite", "")


def test_all_tables_are_explicit_allowlist():
    assert len(PERSONAL_TABLES) == len(set(PERSONAL_TABLES))
    assert "parenting_knowledge" not in PERSONAL_TABLES
