import asyncio

from app.services.offline_telegram_simulator import FakeTelegramTransport
from app.services.outbound_delivery import deliver_user_reserved


def test_failure_before_acceptance_stays_ambiguous_without_replay(tmp_path):
    simulator = FakeTelegramTransport(fail_before_accept=True)
    db = tmp_path / "offline.sqlite"

    async def send():
        await simulator.send_message("pre-accept-event")

    try:
        asyncio.run(deliver_user_reserved(db, "17", "pre-accept-event", send))
    except ConnectionError:
        pass
    else:
        raise AssertionError("Expected simulated network failure")

    assert not asyncio.run(deliver_user_reserved(db, "17", "pre-accept-event", send))
    assert simulator.calls["pre-accept-event"] == 1
    assert simulator.messages == []


def test_distinct_event_keys_are_independent(tmp_path):
    simulator = FakeTelegramTransport()
    db = tmp_path / "offline.sqlite"

    async def scenario():
        for event in ("response-0", "response-1"):
            async def send(key=event):
                await simulator.send_message(key)
            assert await deliver_user_reserved(db, "17", event, send)

    asyncio.run(scenario())
    assert [event for event, _ in simulator.messages] == ["response-0", "response-1"]
