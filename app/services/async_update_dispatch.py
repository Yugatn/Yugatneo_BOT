"""Async dispatch for Telegram polling with a persistent processing lease.

A failed update must NOT advance the polling offset. Telegram retains the
update until acknowledged by a later getUpdates offset. A lease prevents
immediate repeated execution after an uncertain failure.
"""
from app.services.update_jobs import enqueue, acquire, complete


async def dispatch_update(db_path, update_id, handler):
    enqueue(db_path, update_id)
    if not acquire(db_path, update_id):
        return False
    await handler()
    complete(db_path, update_id)
    return True
