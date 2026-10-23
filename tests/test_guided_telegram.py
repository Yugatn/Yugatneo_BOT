import asyncio
import sqlite3

from app import telegram_polling as bot


def test_guided_reflection_in_memory_summary_and_cancel(tmp_path, monkeypatch):
    db = tmp_path / "bot.sqlite3"
    monkeypatch.setattr(bot, "DB_PATH", db)
    bot.init_db()
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO bot_security(telegram_user_id, window_start, verified) "
            "VALUES ('202', 0, 1)"
        )
    bot.GUIDED_SESSIONS.clear()
    sent = []

    async def fake_send(client, token, chat_id, text, keyboard=bot.MENU):
        sent.append(text)

    monkeypatch.setattr(bot, "send", fake_send)

    async def message(text):
        await bot.handle_message(
            None, "test-token",
            {"from": {"id": 202}, "chat": {"id": 202, "type": "private"}, "text": text}
        )

    async def run():
        await message("/guided")
        assert "202" in bot.GUIDED_SESSIONS
        await message("Learn guitar")
        await message("/skip")
        await message("Limited time")
        await message("A mentor")
        await message("Practice ten minutes")
        assert "202" not in bot.GUIDED_SESSIONS
        assert "Learn guitar" in sent[-1]
        assert "Пропущено" in sent[-1]
        await message("/guided")
        await message("/cancel")
        assert "202" not in bot.GUIDED_SESSIONS

    asyncio.run(run())
    with sqlite3.connect(db) as conn:
        for table in ("bot_state", "wheel_scores", "career_reflection"):
            values = conn.execute(f"SELECT * FROM {table}").fetchall()
            assert "Learn guitar" not in repr(values)
