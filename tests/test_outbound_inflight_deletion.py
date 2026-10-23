import asyncio
import sqlite3

from app.services.outbound_delivery import deliver_user_reserved
from app.services.personal_data import delete_telegram_user_records


def test_delete_while_send_waits_does_not_recreate_record(tmp_path):
    db = tmp_path / "race.sqlite"
    started = asyncio.Event()
    release = asyncio.Event()

    async def send():
        started.set()
        await release.wait()

    async def scenario():
        task = asyncio.create_task(
            deliver_user_reserved(db, "17", "evt-20", send)
        )
        await started.wait()
        removed = delete_telegram_user_records(db, "17")
        assert removed["user_outbound_delivery"] == 1
        release.set()
        assert await task is False

    asyncio.run(scenario())
    with sqlite3.connect(db) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM user_outbound_delivery"
        ).fetchone()[0] == 0
