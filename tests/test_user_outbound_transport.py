import asyncio
import sqlite3

from app.services.outbound_delivery import deliver_user_reserved, confirm_user_delivery
from app.services.personal_data import delete_telegram_user_records


def test_user_outbound_success_and_cleanup(tmp_path):
    db = tmp_path / "delivery.sqlite"
    calls = []

    async def send():
        calls.append(1)

    assert asyncio.run(deliver_user_reserved(db, "42", "event-42", send))
    assert not asyncio.run(deliver_user_reserved(db, "42", "event-42", send))
    assert calls == [1]
    assert not confirm_user_delivery(db, "43", "event-42")
    assert delete_telegram_user_records(db, "42")["user_outbound_delivery"] == 1
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM user_outbound_delivery").fetchone()[0] == 0
