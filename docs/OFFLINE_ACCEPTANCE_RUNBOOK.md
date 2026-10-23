# Offline acceptance — reproducible operator procedure

No production token, webhook, server, actual user records or external API are
needed for this exercise. Run it in a clean local virtual environment or CI.

## Commands

```bash
python -m pip install -r requirements.txt
python -m pip check
python -m compileall -q app tests
python -m pytest -q
python -m app.services.offline_acceptance
```

The last command creates temporary SQLite databases, generates a throwaway
Fernet key in memory, writes only synthetic reflection content, tests SQLite
backup and restore, checks decryption, simulates a normal send and a lost
acknowledgement, then removes the synthetic user's records. Temporary files
are discarded when the command exits.

Expected acceptance output is one JSON object with:

- `offline_only: true`
- `backup_restore: "passed"`
- `encrypted_report_readable: "passed"`
- `user_data_deletion: "passed"`
- `normal_send: "passed"`
- `uncertain_send: "passed"`

All five status fields and both supported Python test jobs must pass. No real
user messages or encryption keys may appear in test logs. Failing, skipped,
or queued checks must not be reported as verified.

## Staging evidence template (manual, not yet completed)

| Evidence | Operator/date | Result | Link or location |
|---|---|---|---|
| Both CI suites on the same release SHA | Pending | Not run for a release | — |
| Offline acceptance on Python 3.11 and 3.12 | Pending | Not signed | — |
| No credentials in test logs | Pending | Not independently reviewed | — |
| Restore and encrypted fixture readability on isolated host | Pending | Not run | — |
| Deletion during a network request / concurrency risk review | Pending | Not approved | — |
| Single polling worker and rollback rehearsal | Pending | Requires staging | — |
| Independent clinical, privacy and security sign-off | Pending | Not approved | — |

## Known limitations

The synthetic transport does not verify Telegram's real behavior. A delivery
reserved before remote acceptance can become permanently ambiguous; no
automatic resend occurs, including after a failure before the network
request. Deleting local data does not recall Telegram messages already
sent. An in-flight operation can still transmit after deletion begins.
The user-scoped ledger does not yet implement a multi-process deletion
barrier or operator reconciliation. The experimental flag must remain OFF
outside isolated tests pending resolution and independent approval.

A green CI result is necessary but does not authorize a public or clinical
service launch.
