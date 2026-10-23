from app.services.outbound_delivery import (
    register_delivery, mark_delivery_ambiguous, delivery_state,
)


def test_delivery_registration_is_idempotent(tmp_path):
    db = tmp_path / "outbound.sqlite"
    register_delivery(db, "update:12:reply:0")
    register_delivery(db, "update:12:reply:0")
    assert delivery_state(db, "update:12:reply:0") == "pending"
    assert mark_delivery_ambiguous(db, "update:12:reply:0")
    register_delivery(db, "update:12:reply:0")
    assert delivery_state(db, "update:12:reply:0") == "ambiguous"
    assert not mark_delivery_ambiguous(db, "update:12:reply:0")


def test_invalid_delivery_key_rejected(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        register_delivery(tmp_path / "outbound.sqlite", "")
