"""SQLite persistence for versioned balance-wheel snapshots.

Callers must supply an authenticated server-side user identifier.
"""
import json
import sqlite3
from app.services.wheel_domain import RayScore, new_snapshot


def ensure_schema(db: sqlite3.Connection) -> None:
    db.execute(
        "CREATE TABLE IF NOT EXISTS wheel_snapshots ("
        "id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, "
        "version INTEGER NOT NULL, created_at TEXT NOT NULL, "
        "answers_json TEXT NOT NULL)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS wheel_snapshots_by_user "
        "ON wheel_snapshots(user_id, id DESC)"
    )


def save(db: sqlite3.Connection, user_id: str, scores: list[RayScore],
         version: int = 1) -> int:
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("authenticated user id required")
    snapshot = new_snapshot(scores, version)
    if not snapshot["answers"]:
        raise ValueError("empty assessment")
    ensure_schema(db)
    result = db.execute(
        "INSERT INTO wheel_snapshots(user_id, version, created_at, answers_json) "
        "VALUES (?, ?, ?, ?)",
        (user_id, version, snapshot["recorded_at"],
         json.dumps(snapshot["answers"], ensure_ascii=False)),
    )
    return int(result.lastrowid)


def history(db: sqlite3.Connection, user_id: str, limit: int = 30) -> list[dict]:
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("authenticated user id required")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    ensure_schema(db)
    rows = db.execute(
        "SELECT id, version, created_at, answers_json "
        "FROM wheel_snapshots WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [
        {"id":id_, "wheel_version":version, "recorded_at":created,
         "answers":json.loads(answers)}
        for id_, version, created, answers in rows
    ]


def erase(db: sqlite3.Connection, user_id: str) -> None:
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("authenticated user id required")
    ensure_schema(db)
    db.execute("DELETE FROM wheel_snapshots WHERE user_id=?", (user_id,))
