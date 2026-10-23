"""Offline integration tests for post-deletion /start state re-creation."""
import asyncio
import sqlite3
import time

from app import telegram_polling as polling
from app.services.personal_data import delete_telegram_user_records


def test_experimental_start_after_deletion_does_not_recreate_state(tmp_path, monkeypatch):
    db = tmp_path / "deleted.sqlite"
    monkeypatch.setattr(polling, "DB_PATH", db)
    monkeypatch.setattr(polling, "outbound_guard_requested", lambda: True)

    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE bot_state (telegram_user_id TEXT PRIMARY KEY, value TEXT)"
        )
    delete_telegram_user_records(db, "17")
    handled = []

    async def fake_handler(client, token, message):
        user_id = str(message["from"]["id"])
        handled.append(user_id)
        with sqlite3.connect(db) as conn:
            conn.execute(
                "INSERT INTO bot_state(telegram_user_id, value) VALUES (?, ?)",
                (user_id, "restarted"),
            )

    monkeypatch.setattr(polling, "handle_message", fake_handler)

    async def scenario():
        for update_id, user_id in ((100, 17), (101, 18)):
            await polling.handle_update_message(
                None, "", update_id,
                {
                    "text": "/start",
                    "date": int(time.time()),
                    "from": {"id": user_id},
                    "chat": {"id": user_id, "type": "private"},
                },
            )

    asyncio.run(scenario())
    assert handled == ["18"]
    with sqlite3.connect(db) as conn:
        assert conn.execute(
            "SELECT telegram_user_id FROM bot_state"
        ).fetchall() == [("18",)]


def test_deletion_command_bypasses_experimental_fence(tmp_path, monkeypatch):
    db = tmp_path / "deleted.sqlite"
    monkeypatch.setattr(polling, "DB_PATH", db)
    monkeypatch.setattr(polling, "outbound_guard_requested", lambda: True)
    delete_telegram_user_records(db, "17")
    handled = []

    async def fake_handler(client, token, message):
        handled.append((message["text"], polling._OUTBOUND_CONTEXT.get()))

    monkeypatch.setattr(polling, "handle_message", fake_handler)
    asyncio.run(polling.handle_update_message(
        None, "", 103,
        {
            "text": "/delete_my_data",
            "from": {"id": 17},
            "chat": {"id": 17, "type": "private"},
        },
    ))
    assert handled == [("/delete_my_data", None)]
