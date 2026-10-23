import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.services.outbound_delivery import deliver_reserved, delivery_state


def test_competing_async_workers_send_at_most_once(tmp_path):
    db = tmp_path / "delivery.sqlite"
    calls = []

    async def send():
        calls.append("network")
        await asyncio.sleep(0.01)

    def worker():
        return asyncio.run(deliver_reserved(db, "telegram:77:0:sendMessage", send))

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: worker(), range(12)))

    assert results.count(True) == 1
    assert results.count(False) == 11
    assert calls == ["network"]
    assert delivery_state(db, "telegram:77:0:sendMessage") == "sent"
