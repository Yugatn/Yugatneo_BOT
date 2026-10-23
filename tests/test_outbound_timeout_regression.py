import asyncio

from app.services.outbound_delivery import deliver_user_reserved


def test_outbound_timeout_preserves_single_attempt(tmp_path):
    db = tmp_path / "timeout.sqlite"
    attempts = []

    async def send():
        attempts.append(1)
        raise TimeoutError("remote response unavailable")

    for expected in (True, False):
        try:
            result = asyncio.run(deliver_user_reserved(db, "17", "evt-17", send))
        except TimeoutError:
            assert expected
        else:
            assert not expected
            assert result is False

    assert attempts == [1]
