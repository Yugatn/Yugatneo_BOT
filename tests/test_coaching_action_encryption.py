"""Coaching action text should be encrypted without changing user-visible reports."""
import asyncio
import sqlite3

from cryptography.fernet import Fernet

from app import telegram_polling as bot
from app.services.diagnostic_encryption import PREFIX


def test_coaching_action_encrypted_and_report_readable(tmp_path, monkeypatch):
    db = tmp_path / "bot.sqlite3"
    monkeypatch.setattr(bot, "DB_PATH", db)
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    bot.init_db()
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO bot_security(telegram_user_id, window_start, verified) "
            "VALUES ('81', 0, 1)"
        )
    sent = []

    async def fake_send(client, token, chat_id, text, keyboard=bot.MENU):
        sent.append(text)

    monkeypatch.setattr(bot, "send", fake_send)

    async def message(text):
        await bot.handle_message(
            None, "test-token",
            {"from": {"id": 81}, "chat": {"id": 81, "type": "private"}, "text": text}
        )

    async def run():
        bot.save_score("81", "Creativity", 7)
        await message("/next_step")
        await message("Creativity")
        await message("Draw a new picture every day")
        await message("/report")
    asyncio.run(run())

    with sqlite3.connect(db) as conn:
        row = conn.execute(
            "SELECT action FROM wheel_actions WHERE telegram_user_id='81'"
        ).fetchone()
    assert row is not None
    assert row[0].startswith(PREFIX)
    assert "Draw a new picture" not in row[0]
    assert "Draw a new picture every day" in sent[-1]
