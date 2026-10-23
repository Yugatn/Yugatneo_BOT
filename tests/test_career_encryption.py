"""Career reflection fields are encrypted at rest when configured."""
import asyncio
import sqlite3

from cryptography.fernet import Fernet
from app import telegram_polling as bot
from app.services.diagnostic_encryption import PREFIX


def test_career_answers_encrypted_and_report_readable(tmp_path, monkeypatch):
    path = tmp_path / "bot.sqlite3"
    monkeypatch.setattr(bot, "DB_PATH", path)
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    bot.init_db()
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO bot_security(telegram_user_id, window_start, verified) "
            "VALUES ('44', 0, 1)"
        )
    messages = []

    async def fake_send(client, token, chat_id, text, keyboard=bot.MENU):
        messages.append(text)

    monkeypatch.setattr(bot, "send", fake_send)

    async def user_message(text):
        await bot.handle_message(
            None, "test-token",
            {"from": {"id": 44}, "chat": {"id": 44, "type": "private"}, "text": text}
        )

    async def run():
        await user_message("/career")
        await user_message("Video games")
        await user_message("Drawing")
        await user_message("Make a prototype")
        await user_message("/report")

    asyncio.run(run())
    with sqlite3.connect(path) as conn:
        values = conn.execute(
            "SELECT interest, skill, next_experiment FROM career_reflection "
            "WHERE telegram_user_id='44'"
        ).fetchone()
    assert values and all(value.startswith(PREFIX) for value in values)
    assert all("Drawing" not in value for value in values)
    assert "Video games" in messages[-1]
    assert "Make a prototype" in messages[-1]
