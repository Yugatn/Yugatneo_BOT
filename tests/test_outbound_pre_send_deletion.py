"""Synthetic regression: deletion after reservation, before network transport."""
import asyncio
import sqlite3

from app.services import outbound_delivery
from app.services.personal_data import delete_telegram_user_records


def test_deletion_after_reservation_prevents_unsent_network_call(tmp_path, monkeypatch):
    database = tmp_path / "race.sqlite"
    actual_reserve = outbound_delivery.reserve_user_delivery
    calls = []

    def reserve_then_delete(db_path, user_id, event_key):
        reserved = actual_reserve(db_path, user_id, event_key)
        delete_telegram_user_records(db_path, user_id)
        return reserved

    async def send():
        calls.append("network")

    monkeypatch.setattr(outbound_delivery, "reserve_user_delivery", reserve_then_delete)
    assert not asyncio.run(
        outbound_delivery.deliver_user_reserved(database, "17", "race-event", send)
    )
    assert calls == []
    with sqlite3.connect(database) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM user_outbound_delivery WHERE telegram_user_id=?",
            ("17",),
        ).fetchone()[0] == 0


def test_new_unblocked_delivery_still_sends(tmp_path):
    database = tmp_path / "unblocked.sqlite"
    calls = []

    async def send():
        calls.append("network")

    assert asyncio.run(
        outbound_delivery.deliver_user_reserved(database, "17", "good-event", send)
    )
    assert calls == ["network"]
