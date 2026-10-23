import asyncio
import time

from app import telegram_polling as polling


def test_safety_and_deletion_messages_bypass_experimental_context(monkeypatch):
    monkeypatch.setattr(polling, "outbound_guard_requested", lambda: True)
    observed = []

    async def handler(client, token, message):
        observed.append((message["text"], polling._OUTBOUND_CONTEXT.get()))

    monkeypatch.setattr(polling, "handle_message", handler)
    base = {"from": {"id": 11}, "chat": {"id": 11, "type": "private"}, "date": int(time.time())}

    async def scenario():
        for index, message in enumerate((
            "/start",
            "I am in immediate danger",
            "🗑 Удалить мои данные",
            "/start extra",
        )):
            await polling.handle_update_message(
                None, "", 100 + index, {**base, "text": message}
            )

    asyncio.run(scenario())
    assert observed[0][1] == (100, "11", 0)
    assert all(context is None for _, context in observed[1:])
    assert polling._OUTBOUND_CONTEXT.get() is None
