import asyncio
import sqlite3

from app.services.outbound_delivery import deliver_user_reserved
from app.services.personal_data import delete_telegram_user_records


def test_deletion_during_outbound_send_does_not_restore_metadata(tmp_path):
    db = tmp_path / "deletion.sqlite"

    async def send():
        result = delete_telegram_user_records(db, "17")
        assert result["user_outbound_delivery"] == 1

    assert not asyncio.run(deliver_user_reserved(db, "17", "evt-19", send))
    with sqlite3.connect(db) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM user_outbound_delivery"
        ).fetchone()[0] == 0
