import asyncio

import pytest

from app.services.async_update_dispatch import dispatch_update
from app.services.update_jobs import status


def test_async_dispatch_marks_success(tmp_path):
    db = tmp_path / "jobs.sqlite"
    calls = []

    async def handler():
        calls.append(1)

    assert asyncio.run(dispatch_update(db, 55, handler))
    assert status(db, 55) == ("done", 1)
    assert not asyncio.run(dispatch_update(db, 55, handler))
    assert calls == [1]


def test_async_dispatch_does_not_ack_failure(tmp_path):
    db = tmp_path / "jobs.sqlite"

    async def handler():
        raise RuntimeError("interrupted")

    with pytest.raises(RuntimeError):
        asyncio.run(dispatch_update(db, 56, handler))
    assert status(db, 56) == ("processing", 1)
