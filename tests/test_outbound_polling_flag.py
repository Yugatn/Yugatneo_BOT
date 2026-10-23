import asyncio
import time

from app import telegram_polling as polling


def test_outbound_context_disabled_by_default(monkeypatch):
    monkeypatch.setattr(polling, "outbound_guard_requested", lambda: False)
    received = []

    async def fake_handler(client, token, message):
        received.append(polling._OUTBOUND_CONTEXT.get())

    monkeypatch.setattr(polling, "handle_message", fake_handler)
    message = {"text": "/start", "from": {"id": 10}, "chat": {"id": 10, "type": "private"}}
    asyncio.run(polling.handle_update_message(None, "", 5, message))
    assert received == [None]


def test_outbound_context_limited_to_private_start(monkeypatch):
    monkeypatch.setattr(polling, "outbound_guard_requested", lambda: True)
    monkeypatch.setattr(polling, "is_user_deletion_fenced", lambda db, user: False)
    received = []

    async def fake_handler(client, token, message):
        received.append(polling._OUTBOUND_CONTEXT.get())

    monkeypatch.setattr(polling, "handle_message", fake_handler)
    base = {"from": {"id": 10}, "chat": {"id": 10, "type": "private"}, "date": int(time.time())}
    async def scenario():
        await polling.handle_update_message(None, "", 5, {**base, "text": "/start"})
        await polling.handle_update_message(None, "", 6, {**base, "text": "/help"})
        await polling.handle_update_message(None, "", 7, {**base, "text": "/delete"})
    asyncio.run(scenario())
    assert received == [(5, "10", 0), None, None]
    assert polling._OUTBOUND_CONTEXT.get() is None
