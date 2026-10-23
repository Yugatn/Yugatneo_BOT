import sqlite3

from app.services.bot_security import check_message, init_security, MAX_MESSAGES


def test_challenge_solved_and_remembered(tmp_path):
    path = str(tmp_path / "security.db")
    status, prompt = check_message(path, "u1", "/start", now=100)
    assert status == "challenge"
    with sqlite3.connect(path) as conn:
        answer = conn.execute(
            "SELECT challenge_answer FROM bot_security WHERE telegram_user_id='u1'"
        ).fetchone()[0]
    status, _ = check_message(path, "u1", answer, now=101)
    assert status == "solved"
    assert check_message(path, "u1", "/start", now=102)[0] == "allow"


def test_throttling_after_verification(tmp_path):
    path = str(tmp_path / "security.db")
    check_message(path, "u2", "/start", now=100)
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE bot_security SET verified=1 WHERE telegram_user_id='u2'")
    outcomes = [check_message(path, "u2", "hello", now=101)[0] for _ in range(MAX_MESSAGES)]
    assert "limited" in outcomes
    assert check_message(path, "u2", "hello", now=162)[0] == "allow"


def test_start_does_not_consume_attempt(tmp_path):
    path = str(tmp_path / "security.db")
    check_message(path, "u3", "/start", now=100)
    assert check_message(path, "u3", "/start", now=101)[0] == "challenge"
    with sqlite3.connect(path) as conn:
        assert conn.execute(
            "SELECT attempts FROM bot_security WHERE telegram_user_id='u3'"
        ).fetchone()[0] == 0
