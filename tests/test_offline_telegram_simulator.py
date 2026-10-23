import asyncio

from app.services.offline_telegram_simulator import FakeTelegramTransport
from app.services.outbound_delivery import deliver_user_reserved


def test_offline_success_and_deduplication(tmp_path):
    fake = FakeTelegramTransport()
    db = tmp_path / "test.sqlite"

    async def send():
        await fake.send_message("event-1")

    assert asyncio.run(deliver_user_reserved(db, "17", "event-1", send))
    assert not asyncio.run(deliver_user_reserved(db, "17", "event-1", send))
    assert fake.calls["event-1"] == 1
    assert len(fake.messages) == 1


def test_lost_acknowledgement_does_not_duplicate(tmp_path):
    fake = FakeTelegramTransport(fail_after_accept=True)
    db = tmp_path / "test.sqlite"

    async def send():
        await fake.send_message("event-2")

    try:
        asyncio.run(deliver_user_reserved(db, "17", "event-2", send))
    except TimeoutError:
        pass
    else:
        raise AssertionError("expected simulated timeout")

    assert not asyncio.run(deliver_user_reserved(db, "17", "event-2", send))
    assert fake.calls["event-2"] == 1
    assert len(fake.messages) == 1
