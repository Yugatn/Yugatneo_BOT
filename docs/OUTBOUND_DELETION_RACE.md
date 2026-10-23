# User deletion and outbound delivery: remaining race

The user-scoped outbound ledger supports deletion through the personal-data
allowlist. A regression test verifies that confirmation does not recreate a
record removed during an in-flight send.

This is **not** a guarantee that deletion cancels a Telegram API request
already in progress. A message may still be delivered after deletion has
started, and Telegram's copy is outside the local SQLite deletion boundary.

Production integration requires an explicit lifecycle policy for in-flight
requests, deletion acknowledgment, and external provider retention. The
metadata-only adapter remains opt-in and disconnected from the polling loop.
