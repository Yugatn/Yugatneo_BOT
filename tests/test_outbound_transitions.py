from app.services.outbound_delivery import (
    register_delivery, mark_delivery_sent, mark_delivery_ambiguous,
    delivery_state, delivery_counts,
)


def test_confirmed_delivery_is_terminal(tmp_path):
    db = tmp_path / "ledger.sqlite"
    register_delivery(db, "event-1")
    assert mark_delivery_sent(db, "event-1")
    assert not mark_delivery_ambiguous(db, "event-1")
    assert not mark_delivery_sent(db, "event-1")
    assert delivery_state(db, "event-1") == "sent"
    assert delivery_counts(db) == {"sent": 1}


def test_ambiguous_delivery_cannot_be_marked_sent_without_review(tmp_path):
    db = tmp_path / "ledger.sqlite"
    register_delivery(db, "event-2")
    assert mark_delivery_ambiguous(db, "event-2")
    assert not mark_delivery_sent(db, "event-2")
    assert delivery_counts(db) == {"ambiguous": 1}
