"""Verify that stored summaries can be opened with the configured key."""
import sqlite3

from app.services.guided_report_storage import read_report


def count_unreadable_reports(db_path):
    with sqlite3.connect(db_path) as conn:
        present = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name='guided_reflection_reports'"
        ).fetchone()
        if not present:
            return {"checked": 0, "unreadable": 0}
        users = [row[0] for row in conn.execute(
            "SELECT telegram_user_id FROM guided_reflection_reports"
        )]
    unreadable = 0
    for user_id in users:
        try:
            read_report(db_path, user_id)
        except (RuntimeError, ValueError):
            unreadable += 1
    return {"checked": len(users), "unreadable": unreadable}
