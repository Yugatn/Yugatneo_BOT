import sqlite3

from app.services.outbound_delivery import (
    confirm_user_delivery, delivery_counts, register_delivery, reserve_user_delivery,
)
from app.services.personal_data import delete_telegram_user_records


def test_outbound_tables_initialize_on_legacy_database(tmp_path):
    database = tmp_path / "legacy.sqlite"
    with sqlite3.connect(database) as conn:
        conn.execute("CREATE TABLE old_business_data (value TEXT NOT NULL)")
        conn.execute("INSERT INTO old_business_data VALUES ('preserve')")

    register_delivery(database, "old-global-event")
    assert reserve_user_delivery(database, "17", "new-scoped-event")
    assert confirm_user_delivery(database, "17", "new-scoped-event")
    assert delivery_counts(database) == {"pending": 1}
    assert delete_telegram_user_records(database, "17")["user_outbound_delivery"] == 1

    with sqlite3.connect(database) as conn:
        assert conn.execute("SELECT value FROM old_business_data").fetchone() == (
            "preserve",
        )
        assert conn.execute(
            "SELECT COUNT(*) FROM user_outbound_delivery"
        ).fetchone()[0] == 0


def test_legacy_and_user_scoped_tables_can_reinitialize(tmp_path):
    database = tmp_path / "legacy.sqlite"
    assert reserve_user_delivery(database, "17", "evt-1")
    assert not reserve_user_delivery(database, "17", "evt-1")
    register_delivery(database, "evt-2")
    register_delivery(database, "evt-2")
    assert delivery_counts(database) == {"pending": 1}
