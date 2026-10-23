"""Offline, synthetic regression tests for deletion vs outbound reservations."""
from concurrent.futures import ThreadPoolExecutor
import sqlite3

from app.services import outbound_deletion_fence as fence
from app.services.outbound_delivery import reserve_user_delivery
from app.services.personal_data import delete_telegram_user_records


def test_deletion_fence_blocks_new_reservations_across_workers(tmp_path, monkeypatch):
    db = tmp_path / "fenced.sqlite"
    monkeypatch.setattr(fence.time, "time", lambda: 10_000)
    assert reserve_user_delivery(db, "17", "before-deletion")
    deleted = delete_telegram_user_records(db, "17")
    assert deleted["user_outbound_delivery"] == 1

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(
            lambda index: reserve_user_delivery(db, "17", f"late-{index}"),
            range(16),
        ))
    assert results == [False] * 16
    assert reserve_user_delivery(db, "18", "other-user")
    with sqlite3.connect(db) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM user_outbound_delivery "
            "WHERE telegram_user_id='17'"
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT expires_at FROM outbound_deletion_fence "
            "WHERE telegram_user_id='17'"
        ).fetchone()[0] == 10_000 + fence.DELETION_FENCE_SECONDS


def test_deletion_fence_expires_and_is_purgeable(tmp_path, monkeypatch):
    db = tmp_path / "expiring.sqlite"
    monkeypatch.setattr(fence.time, "time", lambda: 20_000)
    delete_telegram_user_records(db, "17")
    assert not reserve_user_delivery(db, "17", "during-block")
    monkeypatch.setattr(
        fence.time, "time", lambda: 20_000 + fence.DELETION_FENCE_SECONDS
    )
    assert reserve_user_delivery(db, "17", "after-expiration")
    # The reservation itself purges this user's expired marker.
    assert fence.purge_expired_deletion_fences(db) == 0
    monkeypatch.setattr(fence.time, "time", lambda: 30_000)
    delete_telegram_user_records(db, "another-user")
    assert fence.purge_expired_deletion_fences(
        db, now=30_000 + fence.DELETION_FENCE_SECONDS
    ) == 1
    assert fence.purge_expired_deletion_fences(
        db, now=30_000 + fence.DELETION_FENCE_SECONDS
    ) == 0


def test_failed_deletion_does_not_create_suppression_marker(tmp_path):
    db = tmp_path / "broken.sqlite"
    with sqlite3.connect(db) as conn:
        # Corrupt the legacy schema: allowlist table lacks the required column.
        conn.execute("CREATE TABLE wheel_scores (something_else TEXT)")
    try:
        delete_telegram_user_records(db, "17")
    except sqlite3.OperationalError:
        pass
    else:
        raise AssertionError("Deletion must fail on incompatible schema")
    with sqlite3.connect(db) as conn:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name='outbound_deletion_fence'"
        ).fetchone()
        assert exists is None
