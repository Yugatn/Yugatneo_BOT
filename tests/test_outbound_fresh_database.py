from app.services.outbound_delivery import (
    confirm_reserved_delivery, delivery_counts, reserve_delivery, delivery_state,
)


def test_confirm_unknown_delivery_initializes_empty_ledger(tmp_path):
    db = tmp_path / "fresh.sqlite"
    assert not confirm_reserved_delivery(db, "unknown")
    assert delivery_counts(db) == {}
    assert reserve_delivery(db, "known")
    assert delivery_state(db, "known") == "ambiguous"


def test_confirm_unknown_does_not_change_existing_reservation(tmp_path):
    db = tmp_path / "existing.sqlite"
    assert reserve_delivery(db, "known")
    assert not confirm_reserved_delivery(db, "other")
    assert delivery_state(db, "known") == "ambiguous"
