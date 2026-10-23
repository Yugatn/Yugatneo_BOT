"""Exercise duplicate delivery through the async dispatcher."""
import asyncio

from app.services.async_update_dispatch import dispatch_update
from app.services.update_jobs import status


def test_async_duplicate_delivery_runs_handler_once(tmp_path):
    db = tmp_path / "updates.sqlite"
    calls = []

    async def handler():
        calls.append("handled")

    async def scenario():
        assert await dispatch_update(db, 51, handler) is True
        assert await dispatch_update(db, 51, handler) is False

    asyncio.run(scenario())
    assert calls == ["handled"]
    assert status(db, 51) == ("done", 1)


def test_async_failed_handler_does_not_mark_done(tmp_path):
    db = tmp_path / "updates.sqlite"

    async def fail():
        raise RuntimeError("simulated failure")

    async def scenario():
        try:
            await dispatch_update(db, 52, fail)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Expected handler failure")

    asyncio.run(scenario())
    assert status(db, 52) == ("processing", 1)
