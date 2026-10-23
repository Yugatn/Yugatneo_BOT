import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.services.outbound_delivery import deliver_user_reserved


def test_competing_workers_share_one_outbound_reservation(tmp_path):
    db = tmp_path / "competing.sqlite"
    sent = []

    async def send():
        sent.append(1)
        await asyncio.sleep(0.01)

    def run(_):
        return asyncio.run(deliver_user_reserved(db, "17", "evt-18", send))

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, range(8)))

    assert results.count(True) == 1
    assert results.count(False) == 7
    assert sent == [1]
