# Telegram polling: quarantine operations

This runbook covers the local SQLite queue. It is not a public moderation API.

## Failure and recovery

A failed handler leaves the Telegram update unacknowledged. The update lease
expires after 120 seconds by default. After three failed processing attempts,
the polling process exits and the update remains in `quarantined` state.
Do not skip the Telegram offset or delete the row to resume service.

1. Stop the bot process and preserve a verified, access-controlled database
   backup before inspecting state.
2. Review aggregate counts using
   `app.services.update_operations.update_metrics(db_path)`.
3. Review quarantined update IDs and attempt counts using
   `app.services.quarantine_inspection.list_quarantined(db_path)`.
   These functions do not reveal message content.
4. Investigate code/configuration failures, run offline tests, and verify
   that retrying the handler cannot repeat harmful external side effects.
5. An authorized operator may explicitly invoke
   `authorized_release(db_path, update_id, token)` from
   `app.services.operator_auth` with a securely provisioned server-side
   `YUGATNEO_OPERATOR_TOKEN` (at least 32 characters)
   while polling is stopped. The action is recorded in
   `update_operator_audit`.
6. Restart the bot and monitor metrics. Never mark a failed update as
   completed solely to restore service.

## Limitations

The new token-gated entry point authenticates possession of a shared secret,
not a named human identity or role. The underlying internal release function
remains callable by trusted Python code with host access. It is not an
independent security boundary against privileged server operators. Restrict database and shell access at the host level.
The audit is not tamper-proof against privileged database operators.
Telegram update IDs can be correlated with other operational records; protect
these records and define a retention policy.

The bot does not persist raw Telegram payloads in the queue. Recovery depends
on Telegram retaining unacknowledged updates. Exactly-once external message
delivery is not guaranteed. Independent privacy, clinical-content, incident
response and penetration reviews remain required before public release.
