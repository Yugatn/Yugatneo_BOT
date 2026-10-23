"""Metadata-only outbound delivery ledger; message bodies are never stored."""
import sqlite3


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
