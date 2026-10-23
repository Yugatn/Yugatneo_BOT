"""Crash-window recovery with an expired processing lease."""
import asyncio
from cryptography.fernet import Fernet

from app.services.async_update_dispatch import dispatch_update
from app.services.idempotent_reflection import save_report_once
from app.services.guided_report_storage import read_report
from app.services.update_jobs import acquire, status


def test_expired_lease_replay_preserves_first_saved_report(tmp_path, monkeypatch):
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    db = tmp_path / "replay.sqlite"
    saved = []

    async def first():
        saved.append(save_report_once(db, "u", "first", 91))
        raise RuntimeError("interrupted")

    async def second():
        saved.append(save_report_once(db, "u", "second", 91))

    async def scenario():
        try:
            await dispatch_update(db, 91, first)
        except RuntimeError:
            pass
        # Force the existing processing lease to expire via a future timestamp.
        assert acquire(db, 91, now=9999999999, lease_seconds=1)
        # The receipt still rejects duplicate writes after a worker takeover.
        await second()

    asyncio.run(scenario())
    assert saved == [True, False]
    assert read_report(db, "u") == "first"
    assert status(db, 91) == ("processing", 2)
