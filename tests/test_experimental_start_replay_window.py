"""No-server tests for replay freshness and the 24-hour deletion window."""
import asyncio

import pytest

from app import telegram_polling as polling
from app.services.outbound_update_freshness import (
    EXPERIMENTAL_START_MAX_AGE_SECONDS,
    is_fresh_experimental_start,
)


@pytest.mark.parametrize(
    ("timestamp", "expected"),
    [
        (1_000_000, True),
        (1_000_000 - EXPERIMENTAL_START_MAX_AGE_SECONDS, True),
        (1_000_000 - EXPERIMENTAL_START_MAX_AGE_SECONDS - 1, False),
        (1_000_000 + 120, True),
        (1_000_000 + 121, False),
        (None, False),
        ("1000000", False),
        (True, False),
        (0, False),
        (-1, False),
    ],
)
def test_bounded_start_freshness(timestamp, expected):
    assert is_fresh_experimental_start(timestamp, now=1_000_000) is expected


def test_experimental_stale_replay_is_not_processed(monkeypatch):
    monkeypatch.setattr(polling, "outbound_guard_requested", lambda: True)
    monkeypatch.setattr(
        "app.services.outbound_update_freshness.time.time", lambda: 1_100_000
    )
    handled = []

    async def fake_handler(client, token, message):
        handled.append((message["text"], polling._OUTBOUND_CONTEXT.get()))

    monkeypatch.setattr(polling, "handle_message", fake_handler)
    base = {"from": {"id": 71}, "chat": {"id": 71, "type": "private"}}

    async def scenario():
        await polling.handle_update_message(
            None, "", 101, {**base, "text": "/start", "date": 1_000_000}
        )
        await polling.handle_update_message(
            None, "", 102, {**base, "text": "/start"}
        )
        await polling.handle_update_message(
            None, "", 103, {**base, "text": "/start", "date": 1_100_000}
        )
        await polling.handle_update_message(
            None, "", 104, {**base, "text": "I need urgent help"}
        )
        await polling.handle_update_message(
            None, "", 105, {**base, "text": "/delete_my_data"}
        )

    asyncio.run(scenario())
    assert handled == [
        ("/start", (103, "71", 0)),
        ("I need urgent help", None),
        ("/delete_my_data", None),
    ]
    assert polling._OUTBOUND_CONTEXT.get() is None


def test_normal_start_remains_available_when_flag_is_off(monkeypatch):
    monkeypatch.setattr(polling, "outbound_guard_requested", lambda: False)
    handled = []

    async def fake_handler(client, token, message):
        handled.append(message["text"])

    monkeypatch.setattr(polling, "handle_message", fake_handler)
    asyncio.run(polling.handle_update_message(
        None, "", 106,
        {"text": "/start", "from": {"id": 71},
         "chat": {"id": 71, "type": "private"}, "date": 1},
    ))
    assert handled == ["/start"]
