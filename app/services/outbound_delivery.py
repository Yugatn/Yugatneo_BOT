"""Metadata-only outbound delivery ledger; message bodies are never stored."""
import sqlite3

from app.services.outbound_deletion_fence import is_delivery_blocked


def register_delivery(db_path, event_key):
    if not isinstance(event_key, str) or not event_key or len(event_key) > 128:
        raise ValueError("Invalid event key")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS outbound_delivery "
            "(event_key TEXT PRIMARY KEY, state TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO outbound_delivery VALUES (?, 'pending')",
            (event_key,),
        )


def mark_delivery_ambiguous(db_path, event_key):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "UPDATE outbound_delivery SET state='ambiguous' "
            "WHERE event_key=? AND state='pending'", (event_key,),
        )
        return cursor.rowcount == 1


def delivery_state(db_path, event_key):
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT state FROM outbound_delivery WHERE event_key=?", (event_key,)
        ).fetchone()
    return row[0] if row else None


def mark_delivery_sent(db_path, event_key):
    """Confirm success only for an action still in pending state."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "UPDATE outbound_delivery SET state='sent' "
            "WHERE event_key=? AND state='pending'", (event_key,),
        )
        return cursor.rowcount == 1


def delivery_counts(db_path):
    """Aggregate delivery states without exposing event identifiers."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS outbound_delivery "
            "(event_key TEXT PRIMARY KEY, state TEXT NOT NULL)"
        )
        rows = conn.execute(
            "SELECT state, COUNT(*) FROM outbound_delivery GROUP BY state"
        ).fetchall()
    return dict(rows)


def reserve_delivery(db_path, event_key):
    """Atomically reserve an action; never auto-retry an uncertain send."""
    if not isinstance(event_key, str) or not event_key or len(event_key) > 128:
        raise ValueError("Invalid event key")
    with sqlite3.connect(db_path, timeout=10) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS outbound_delivery "
            "(event_key TEXT PRIMARY KEY, state TEXT NOT NULL)"
        )
        cursor = conn.execute(
            "INSERT OR IGNORE INTO outbound_delivery VALUES (?, 'ambiguous')",
            (event_key,),
        )
        return cursor.rowcount == 1


def confirm_reserved_delivery(db_path, event_key):
    """Confirm an explicitly reserved send after a successful API response."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS outbound_delivery "
            "(event_key TEXT PRIMARY KEY, state TEXT NOT NULL)"
        )
        cursor = conn.execute(
            "UPDATE outbound_delivery SET state='sent' "
            "WHERE event_key=? AND state='ambiguous'", (event_key,),
        )
        return cursor.rowcount == 1


async def deliver_reserved(db_path, event_key, send_callable):
    """Opt-in transport adapter; no automatic replay after an unknown outcome."""
    if not reserve_delivery(db_path, event_key):
        return False
    try:
        await send_callable()
    except Exception:
        # Keep ambiguous: remote acceptance is unknown.
        raise
    confirm_reserved_delivery(db_path, event_key)
    return True


def outbound_event_key(update_id, response_index, action="sendMessage"):
    """Deterministic, non-content identifier for one Telegram response."""
    if type(update_id) is not int or update_id < 0:
        raise ValueError("update_id must be a non-negative integer")
    if type(response_index) is not int or response_index < 0:
        raise ValueError("response_index must be a non-negative integer")
    if action not in ("sendMessage", "editMessageText"):
        raise ValueError("Unsupported outbound action")
    key = f"telegram:{update_id}:{response_index}:{action}"
    if len(key) > 128:
        raise ValueError("Outbound event key too long")
    return key


def reserve_user_delivery(db_path, user_id, event_key):
    """Reserve a user-scoped outbound event in a separate, deletable ledger."""
    if not isinstance(user_id, str) or not user_id:
        raise ValueError("Missing user ID")
    if not isinstance(event_key, str) or not event_key or len(event_key) > 128:
        raise ValueError("Invalid event key")
    with sqlite3.connect(db_path, timeout=10) as conn:
        # Serialize reservation and deletion across all SQLite processes.
        conn.execute("BEGIN IMMEDIATE")
        if is_delivery_blocked(conn, user_id):
            return False
        conn.execute(
            "CREATE TABLE IF NOT EXISTS user_outbound_delivery "
            "(event_key TEXT PRIMARY KEY, telegram_user_id TEXT NOT NULL, "
            "state TEXT NOT NULL)"
        )
        result = conn.execute(
            "INSERT OR IGNORE INTO user_outbound_delivery "
            "(event_key, telegram_user_id, state) VALUES (?, ?, 'ambiguous')",
            (event_key, user_id),
        )
        return result.rowcount == 1


def confirm_user_delivery(db_path, user_id, event_key):
    """Record success only for the matching user's reserved event."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS user_outbound_delivery "
            "(event_key TEXT PRIMARY KEY, telegram_user_id TEXT NOT NULL, "
            "state TEXT NOT NULL)"
        )
        cursor = conn.execute(
            "UPDATE user_outbound_delivery SET state='sent' "
            "WHERE event_key=? AND telegram_user_id=? AND state='ambiguous'",
            (event_key, user_id),
        )
        return cursor.rowcount == 1


async def deliver_user_reserved(db_path, user_id, event_key, send_callable):
    """Optional user-scoped transport; uncertainty suppresses automatic replay."""
    if not reserve_user_delivery(db_path, user_id, event_key):
        return False
    await send_callable()
    return confirm_user_delivery(db_path, user_id, event_key)
