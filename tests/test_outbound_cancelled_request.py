import asyncio

from app.services.outbound_delivery import deliver_user_reserved


def test_cancellation_preserves_deduplication(tmp_path):
    db = tmp_path / "cancel.sqlite"
    entered = asyncio.Event()
    calls = []

    async def network_call():
        calls.append(1)
        entered.set()
        await asyncio.Event().wait()

    async def scenario():
        task = asyncio.create_task(
            deliver_user_reserved(db, "17", "cancel-event", network_call)
        )
        await entered.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert await deliver_user_reserved(
            db, "17", "cancel-event", network_call
        ) is False

    asyncio.run(scenario())
    assert calls == [1]
