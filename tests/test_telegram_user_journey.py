"""End-to-end Telegram handler smoke test without Telegram or OpenAI access."""
import asyncio
import sqlite3

from app import telegram_polling as bot


def test_private_chat_captcha_wheel_report_and_delete(tmp_path, monkeypatch):
    db = tmp_path / "bot.sqlite3"
    monkeypatch.setattr(bot, "DB_PATH", db)
    bot.init_db()
    sent = []

    async def fake_send(client, token, chat_id, text, keyboard=bot.MENU):
        sent.append((chat_id, text))

    monkeypatch.setattr(bot, "send", fake_send)

    async def message(text, *, chat_type="private", user_id=77):
        await bot.handle_message(
            None, "fake-token",
            {"from": {"id": user_id, "is_bot": False},
             "chat": {"id": user_id, "type": chat_type},
             "message_id": len(sent) + 1, "text": text},
        )

    async def journey():
        await message("/start", chat_type="group")
        assert not sent, "Group messages must not trigger private coaching."
        await message("/start")
        assert "?" in sent[-1][1], "New user should receive a challenge."
        with sqlite3.connect(db) as conn:
            answer = conn.execute(
                "SELECT challenge_answer FROM bot_security WHERE telegram_user_id='77'"
            ).fetchone()[0]
        await message(answer)
        assert "Verification complete" in sent[-1][1]
        await message("/start")
        assert "Yugatn" in sent[-1][1]
        await message("/wheel")
        await message("Creativity")
        await message("8")
        await message("/report")
        assert "Creativity" in sent[-1][1]
        await message("/delete_my_data")
        with sqlite3.connect(db) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM wheel_scores WHERE telegram_user_id='77'"
            ).fetchone()[0] == 0
            assert conn.execute(
                "SELECT COUNT(*) FROM bot_security WHERE telegram_user_id='77'"
            ).fetchone()[0] == 0

    asyncio.run(journey())


def test_rejects_oversized_input_before_database(tmp_path, monkeypatch):
    db = tmp_path / "bot.sqlite3"
    monkeypatch.setattr(bot, "DB_PATH", db)
    sent = []

    async def fake_send(client, token, chat_id, text, keyboard=bot.MENU):
        sent.append(text)

    monkeypatch.setattr(bot, "send", fake_send)

    async def run():
        await bot.handle_message(
            None, "fake-token",
            {"from": {"id": 5}, "chat": {"id": 5, "type": "private"},
             "text": "x" * 4001},
        )

    asyncio.run(run())
    assert "too long" in sent[-1]
    assert not db.exists()
