"""End-to-end, offline opt-in polling check against the deletion fence."""
import asyncio
import time

from app import telegram_polling as polling
from app.services.personal_data import delete_telegram_user_records


def test_flagged_private_start_does_not_send_after_deletion(tmp_path, monkeypatch):
    db = tmp_path / "flagged.sqlite"
    monkeypatch.setattr(polling, "DB_PATH", db)
    monkeypatch.setattr(polling, "outbound_guard_requested", lambda: True)
    delete_telegram_user_records(db, "11")
    outgoing = []

    async def fake_api(client, token, method, payload=None):
        outgoing.append((method, payload["chat_id"]))
        return {"message_id": len(outgoing)}

    async def fake_handler(client, token, message):
        await polling.send(client, token, message["chat"]["id"], "Hello", None)

    monkeypatch.setattr(polling, "api", fake_api)
    monkeypatch.setattr(polling, "handle_message", fake_handler)

    async def scenario():
        await polling.handle_update_message(
            None, "fake-token", 80,
            {"from": {"id": 11}, "chat": {"id": 11, "type": "private"}, "text": "/start", "date": int(time.time())}
        )
        assert outgoing == []
        await polling.handle_update_message(
            None, "fake-token", 81,
            {"from": {"id": 12}, "chat": {"id": 12, "type": "private"}, "text": "/start"}
        )

    asyncio.run(scenario())
    assert outgoing == [("sendMessage", 12)]
    assert polling._OUTBOUND_CONTEXT.get() is None
