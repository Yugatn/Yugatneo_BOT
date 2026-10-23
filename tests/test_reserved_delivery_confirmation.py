from app.services.outbound_delivery import (
    reserve_delivery, confirm_reserved_delivery, delivery_state,
)


def test_reserved_send_can_be_confirmed_once(tmp_path):
    db = tmp_path / "outbound.sqlite"
    assert reserve_delivery(db, "update-1")
    assert confirm_reserved_delivery(db, "update-1")
    assert delivery_state(db, "update-1") == "sent"
    assert not confirm_reserved_delivery(db, "update-1")
    assert not reserve_delivery(db, "update-1")


def test_unknown_reservation_cannot_be_confirmed(tmp_path):
    db = tmp_path / "outbound.sqlite"
    assert not confirm_reserved_delivery(db, "missing")
