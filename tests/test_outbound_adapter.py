import asyncio
import pytest
from app.services.outbound_delivery import deliver_reserved, delivery_state


def test_successful_send_is_not_replayed(tmp_path):
    db = tmp_path / "outbound.sqlite"
    calls = []

    async def send():
        calls.append(1)

    assert asyncio.run(deliver_reserved(db, "reply:1", send))
    assert not asyncio.run(deliver_reserved(db, "reply:1", send))
    assert calls == [1]
    assert delivery_state(db, "reply:1") == "sent"


def test_failed_send_remains_ambiguous(tmp_path):
    db = tmp_path / "outbound.sqlite"
    calls = []

    async def fail():
        calls.append(1)
        raise TimeoutError("acknowledgement missing")

    with pytest.raises(TimeoutError):
        asyncio.run(deliver_reserved(db, "reply:2", fail))
    assert not asyncio.run(deliver_reserved(db, "reply:2", fail))
    assert calls == [1]
    assert delivery_state(db, "reply:2") == "ambiguous"
