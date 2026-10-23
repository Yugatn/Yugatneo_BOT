"""Offline job dispatcher for synchronous handlers."""
from app.services.update_jobs import enqueue, acquire, complete


def process_once(db_path, update_id, handler, now=None):
    enqueue(db_path, update_id)
    if not acquire(db_path, update_id, now=now):
        return False
    handler()
    complete(db_path, update_id)
    return True
