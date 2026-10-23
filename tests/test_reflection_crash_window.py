"""Simulate a crash after saving a reflection but before update completion."""
import asyncio

from cryptography.fernet import Fernet

from app.services.async_update_dispatch import dispatch_update
from app.services.guided_report_storage import read_report
from app.services.idempotent_reflection import save_report_once
from app.services.update_jobs import status


def test_replayed_update_does_not_overwrite_saved_reflection(tmp_path, monkeypatch):
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    db = tmp_path / "bot.sqlite"
    writes = []

    async def interrupted():
        writes.append(save_report_once(db, "person", "original", 87))
        raise RuntimeError("crash after save")

    async def replayed():
        writes.append(save_report_once(db, "person", "overwritten", 87))

    async def scenario():
        try:
            await dispatch_update(db, 87, interrupted)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Expected interruption")
        assert status(db, 87) == ("processing", 1)
        # The lease is still held, so the immediate replay is deferred.
        assert not await dispatch_update(db, 87, replayed)

    asyncio.run(scenario())
    assert writes == [True]
    assert read_report(db, "person") == "original"
    assert save_report_once(db, "person", "overwritten", 87) is False
    assert read_report(db, "person") == "original"
