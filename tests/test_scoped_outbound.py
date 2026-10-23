import sqlite3

from app.services.outbound_delivery import reserve_user_delivery
from app.services.personal_data import delete_telegram_user_records


def test_scoped_outbound_records(tmp_path):
    db = tmp_path / "test.sqlite"
    assert reserve_user_delivery(db, "11", "event-11")
    assert reserve_user_delivery(db, "22", "event-22")
    assert not reserve_user_delivery(db, "11", "event-11")
    counts = delete_telegram_user_records(db, "11")
    assert counts["user_outbound_delivery"] == 1
    with sqlite3.connect(db) as conn:
        remaining = conn.execute(
            "SELECT telegram_user_id FROM user_outbound_delivery"
        ).fetchall()
    assert remaining == [("22",)]
