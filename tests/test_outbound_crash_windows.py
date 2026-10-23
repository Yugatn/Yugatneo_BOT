import asyncio
import pytest
from app.services.outbound_delivery import deliver_reserved, delivery_state


def test_crash_after_remote_acceptance_does_not_replay(tmp_path):
    db = tmp_path / "outbound.sqlite"
    sent = []

    async def remote_accepted_but_ack_lost():
        sent.append("accepted")
        raise ConnectionError("ack lost")

    with pytest.raises(ConnectionError):
        asyncio.run(deliver_reserved(db, "message:42", remote_accepted_but_ack_lost))

    assert delivery_state(db, "message:42") == "ambiguous"
    assert asyncio.run(deliver_reserved(db, "message:42", remote_accepted_but_ack_lost)) is False
    assert sent == ["accepted"]


def test_crash_before_network_call_does_not_silently_replay(tmp_path):
    db = tmp_path / "outbound.sqlite"
    async def network_call():
        raise RuntimeError("transport unavailable")

    with pytest.raises(RuntimeError):
        asyncio.run(deliver_reserved(db, "message:43", network_call))
    assert delivery_state(db, "message:43") == "ambiguous"
