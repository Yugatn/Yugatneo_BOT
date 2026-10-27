"""Offline Telegram routing regression tests for coaching privacy and safety.

These tests use synthetic IDs and messages. No network, bot token, or real data.
"""
import asyncio

from app import telegram_polling as polling
from app.services.coaching_session import Session, Stage, advance


def _message(text):
    return {
        "from": {"id": 42, "is_bot": False},
        "chat": {"id": 42, "type": "private"},
        "text": text,
    }


def _active_session():
    session, _ = advance(Session(), "да")
    session, _ = advance(session, "личная цель")
    assert session.stage is Stage.EVIDENCE
    return session


def _fake_transport(monkeypatch):
    sent = []

    async def send(client, token, chat_id, message, keyboard=None):
        sent.append(message)

    monkeypatch.setattr(polling, "send", send)
    monkeypatch.setattr(polling, "check_message", lambda *args: ("allow", None))
    monkeypatch.setattr(polling, "COACHING_SESSIONS", {"42": _active_session()})
    monkeypatch.setattr(polling, "GUIDED_SESSIONS", {})
    monkeypatch.setattr(polling, "GUIDED_PENDING", {})
    return sent


def test_crisis_interrupts_coaching_before_regular_commands(monkeypatch):
    sent = _fake_transport(monkeypatch)
    states = []
    monkeypatch.setattr(polling, "set_state", lambda *args: states.append(args))

    asyncio.run(polling.handle_message(
        None, "synthetic-token", _message("сейчас хочу покончить с собой")
    ))
    assert "42" not in polling.COACHING_SESSIONS
    assert states == [("42", "menu")]
    assert len(sent) == 1
    assert "экстренную службу" in sent[0]


def test_delete_interrupts_coaching_and_calls_data_erasure(monkeypatch):
    sent = _fake_transport(monkeypatch)
    erased = []
    monkeypatch.setattr(
        polling, "delete_telegram_user_records",
        lambda path, user: erased.append(user),
    )
    from app.services import diagnostic_flow
    monkeypatch.setattr(
        diagnostic_flow, "clear_diagnostic",
        lambda channel, user: erased.append((channel, user)),
    )

    asyncio.run(polling.handle_message(
        None, "synthetic-token", _message("/delete_my_data")
    ))
    assert "42" not in polling.COACHING_SESSIONS
    assert erased == ["42", ("telegram", "42")]
    assert "удалены" in sent[0]


def test_declined_consent_closes_coaching_in_telegram(monkeypatch):
    sent = _fake_transport(monkeypatch)
    polling.COACHING_SESSIONS["42"] = Session()

    asyncio.run(polling.handle_message(
        None, "synthetic-token", _message("нет")
    ))
    assert "42" not in polling.COACHING_SESSIONS
    assert "без обязательств" in sent[0]


def test_cancel_discards_in_memory_answers(monkeypatch):
    sent = _fake_transport(monkeypatch)

    asyncio.run(polling.handle_message(
        None, "synthetic-token", _message("/cancel")
    ))
    assert "42" not in polling.COACHING_SESSIONS
    assert "не сохранены" in sent[0]
