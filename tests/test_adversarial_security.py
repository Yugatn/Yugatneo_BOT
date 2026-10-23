"""Adversarial, fully offline checks. No attack traffic is sent to Telegram."""
import asyncio
import io
import logging
import sqlite3

import httpx

from app import telegram_polling as bot
from app.services.bot_security import check_message, MAX_MESSAGES


def test_telegram_http_error_does_not_expose_secret():
    token = "123456:SUPER_SECRET_TOKEN_NEVER_LOG"
    async def run():
        def fail(request):
            return httpx.Response(403, json={"ok": False, "description": "forbidden"})
        async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
            await bot.api(client, token, "sendMessage", {"chat_id": 1, "text": "hello"})
    try:
        asyncio.run(run())
        assert False, "Expected sanitized failure"
    except RuntimeError as exc:
        assert token not in str(exc)
        assert "details redacted" in str(exc)
        assert exc.__cause__ is None


def test_sql_injection_payload_cannot_change_another_users_verification(tmp_path):
    db = str(tmp_path / "security.sqlite")
    check_message(db, "victim", "/start", now=100)
    malicious = "victim' OR '1'='1"
    check_message(db, malicious, "/start", now=101)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM bot_security").fetchone()[0] == 2
        assert conn.execute(
            "SELECT verified FROM bot_security WHERE telegram_user_id=?",
            ("victim",),
        ).fetchone()[0] == 0


def test_spam_is_rate_limited_even_for_verified_user(tmp_path):
    db = str(tmp_path / "security.sqlite")
    check_message(db, "attacker", "/start", now=100)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE bot_security SET verified=1 WHERE telegram_user_id='attacker'")
    results = [check_message(db, "attacker", "spam", now=101)[0]
               for _ in range(MAX_MESSAGES + 2)]
    assert results[-1] == "limited"
    assert check_message(db, "attacker", "normal", now=161)[0] == "allow"


def test_private_chat_only_and_oversize_rejection(tmp_path, monkeypatch):
    db = tmp_path / "security.sqlite"
    monkeypatch.setattr(bot, "DB_PATH", db)
    messages = []
    async def fake_send(client, token, chat_id, text, keyboard=bot.MENU):
        messages.append(text)
    monkeypatch.setattr(bot, "send", fake_send)
    async def run():
        await bot.handle_message(None, "token", {
            "from": {"id": 1}, "chat": {"id": 1, "type": "group"},
            "text": "/start"})
        await bot.handle_message(None, "token", {
            "from": {"id": 1}, "chat": {"id": 1, "type": "private"},
            "text": "X" * 4001})
    asyncio.run(run())
    assert len(messages) == 1
    assert "too long" in messages[0]
    assert not db.exists()
