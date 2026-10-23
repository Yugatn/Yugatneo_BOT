"""Read-only, content-free inspection of quarantined Telegram updates."""
import sqlite3


def list_quarantined(db_path, limit=50):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")
    with sqlite3.connect(db_path, timeout=10) as conn:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='update_jobs'"
        ).fetchone()
        if not exists:
            return []
        rows = conn.execute(
            "SELECT update_id, attempts FROM update_jobs "
            "WHERE state='quarantined' ORDER BY update_id LIMIT ?", (limit,)
        ).fetchall()
    return [{"update_id": row[0], "attempts": row[1]} for row in rows]
