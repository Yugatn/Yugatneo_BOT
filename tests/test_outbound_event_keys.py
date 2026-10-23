import pytest

from app.services.outbound_delivery import outbound_event_key, reserve_delivery


def test_outbound_event_keys_are_deterministic_and_distinct(tmp_path):
    first = outbound_event_key(123, 0)
    assert first == outbound_event_key(123, 0)
    assert first != outbound_event_key(123, 1)
    assert first != outbound_event_key(124, 0)
    assert first != outbound_event_key(123, 0, "editMessageText")
    db = tmp_path / "outbound.sqlite"
    assert reserve_delivery(db, first)
    assert not reserve_delivery(db, first)


@pytest.mark.parametrize("update_id,index,action", [
    (-1, 0, "sendMessage"),
    (1, -1, "sendMessage"),
    (True, 0, "sendMessage"),
    (1, 0, "deleteMessage"),
])
def test_outbound_event_key_rejects_invalid_values(update_id, index, action):
    with pytest.raises(ValueError):
        outbound_event_key(update_id, index, action)
