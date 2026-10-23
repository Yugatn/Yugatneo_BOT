import asyncio

from app import telegram_polling as polling


def test_invalid_envelopes_are_ignored_without_network(monkeypatch):
    monkeypatch.setattr(polling, "outbound_guard_requested", lambda: True)
    accepted = []

    async def fake_handler(client, token, message):
        accepted.append(message)

    monkeypatch.setattr(polling, "handle_message", fake_handler)

    messages = [
        None,
        [],
        "bad",
        {"text": "/start", "from": [], "chat": {}},
        {"text": "/start", "from": {"id": 17}, "chat": None},
        {"text": "/start", "from": {"id": 17}, "chat": "private"},
    ]

    async def scenario():
        for message in messages:
            await polling.handle_update_message(None, "", 100, message)

    asyncio.run(scenario())
    assert accepted == []
    assert polling._OUTBOUND_CONTEXT.get() is None


def test_invalid_start_identifiers_do_not_enable_outbound_guard(monkeypatch):
    monkeypatch.setattr(polling, "outbound_guard_requested", lambda: True)
    contexts = []

    async def fake_handler(client, token, message):
        contexts.append(polling._OUTBOUND_CONTEXT.get())

    monkeypatch.setattr(polling, "handle_message", fake_handler)
    base = {"text": "/start", "chat": {"id": 17, "type": "private"}}
    messages = [
        {**base, "from": {"id": True}},
        {**base, "from": {"id": "17"}},
        {**base, "from": {"id": 0}},
        {**base, "from": {"id": 18}},
        {**base, "from": {"id": 17, "is_bot": True}},
        {**base, "from": {"id": 17}, "text": "/start extra"},
    ]

    async def scenario():
        for message in messages:
            await polling.handle_update_message(None, "", 101, message)
        await polling.handle_update_message(
            None, "", "not-a-number", {**base, "from": {"id": 17}}
        )

    asyncio.run(scenario())
    assert contexts == [None] * 7
    assert polling._OUTBOUND_CONTEXT.get() is None
