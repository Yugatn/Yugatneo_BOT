from concurrent.futures import ThreadPoolExecutor

from app.services.outbound_delivery import reserve_delivery, delivery_state


def test_outbound_reservation_allows_only_one_worker(tmp_path):
    db = tmp_path / "outbound.sqlite"
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: reserve_delivery(db, "event-100"), range(20)))
    assert results.count(True) == 1
    assert results.count(False) == 19
    assert delivery_state(db, "event-100") == "ambiguous"


def test_outbound_reservation_rejects_invalid_key(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        reserve_delivery(tmp_path / "outbound.sqlite", "")
