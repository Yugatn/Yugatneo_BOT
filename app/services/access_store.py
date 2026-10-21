"""Small SQLite access store for the MVP. Use PostgreSQL + migrations for production."""
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from app.core.config import get_settings


def _db_path() -> str:
    url = get_settings().database_url
    if not url.startswith("sqlite:///"):
        raise RuntimeError("MVP access store currently supports SQLite URLs only")
    return url.removeprefix("sqlite:///")


def _connect() -> sqlite3.Connection:
    path = _db_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_access (
            user_key TEXT PRIMARY KEY,
            free_questions_used INTEGER NOT NULL DEFAULT 0,
            total_questions_served INTEGER NOT NULL DEFAULT 0,
            subscription_active INTEGER NOT NULL DEFAULT 0,
            subscription_expires_at TEXT
        )
    """)
    return conn


def user_key(channel: str, external_user_id: str) -> str:
    # Pseudonymous identifier; still personal data in many jurisdictions.
    raw = f"{channel}:{external_user_id}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def claim_question(channel: str, external_user_id: str, free_limit: int = 7) -> dict:
    """Atomically reserve the next catalogue question or report paywall."""
    key = user_key(channel, external_user_id)
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT OR IGNORE INTO user_access(user_key) VALUES (?)", (key,))
        row = conn.execute("SELECT * FROM user_access WHERE user_key = ?", (key,)).fetchone()
        expires = row["subscription_expires_at"]
        active = bool(row["subscription_active"]) and (
            not expires or datetime.fromisoformat(expires) > datetime.now(timezone.utc)
        )
        if not active and row["free_questions_used"] >= free_limit:
            conn.execute("COMMIT")
            return {"allowed": False, "reason": "subscription_required", "remaining_free": 0}
        index = row["total_questions_served"]
        free_used = row["free_questions_used"]
        if not active:
            free_used += 1
        conn.execute(
            "UPDATE user_access SET free_questions_used=?, total_questions_served=? WHERE user_key=?",
            (free_used, index + 1, key),
        )
        conn.execute("COMMIT")
        return {
            "allowed": True,
            "reason": "active_subscription" if active else "free_question_available",
            "remaining_free": max(0, free_limit - free_used),
            "question_index": index,
        }
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
