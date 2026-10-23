import sqlite3
import pytest
from app.services.wheel_domain import RayScore
from app.services.wheel_snapshot_store import save, history, erase


def test_roundtrip_and_user_isolation():
    with sqlite3.connect(":memory:") as db:
        save(db, "alice", [RayScore("health", 0), RayScore("work", 8)])
        save(db, "bob", [RayScore("health", 9)])
        assert [x["score"] for x in history(db, "alice")[0]["answers"]] == [0, 8]
        assert len(history(db, "bob")) == 1
        erase(db, "alice")
        assert history(db, "alice") == []
        assert len(history(db, "bob")) == 1


def test_rejects_invalid_data():
    with sqlite3.connect(":memory:") as db:
        with pytest.raises(ValueError):
            save(db, "alice", [])
        with pytest.raises(ValueError):
            save(db, "", [RayScore("health", 3)])
        with pytest.raises(ValueError):
            history(db, "alice", 101)


def test_versions_and_order():
    with sqlite3.connect(":memory:") as db:
        save(db, "alice", [RayScore("health", 2)], 1)
        save(db, "alice", [RayScore("health", 5)], 2)
        assert [row["wheel_version"] for row in history(db, "alice")] == [2, 1]
