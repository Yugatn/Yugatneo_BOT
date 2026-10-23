# Outbound delivery and user deletion — bounded suppression

## Implemented in the experimental path

The private-chat `/start` response uses a user-scoped outbound receipt only
when `YUGATNEO_EXPERIMENTAL_OUTBOUND=true` and `APP_ENV` is
`development`, `test`, or `staging`. The flag is OFF by default;
`production` and unknown environments cannot enable this path.
Safety messages, normal interactions and deletion acknowledgements retain
the ordinary Telegram transport.

Deleting a user's local records now also writes a **24-hour deletion fence**
inside the **same SQLite `BEGIN IMMEDIATE` transaction**. New outbound
reservations check that fence under their own `BEGIN IMMEDIATE` transaction.
SQLite writer serialization means a different Python process cannot commit a
new experimental outbound reservation after the deletion transaction commits
while that fence is active.

The fence retains the Telegram user identifier and an expiry timestamp but
never saves a message body or psychological report. This identifier is **still
personal data**, retained temporarily as an anti-replay operational exception.
Expired markers are removed on bot startup, at least hourly while the polling
worker is running, or opportunistically when the user is checked again.
An offline maintenance function `purge_expired_deletion_fences(db_path)`
also exists. If the bot is offline beyond expiry, the marker remains until
the next cleanup run. This retention mechanism requires privacy approval.

The experimental transport now checks the fence a second time immediately
before invoking the network sender, closing the testable deletion window
between reservation and send initiation. In addition, experimental /start
handling now checks the fence before running the handler, avoiding the
previous case in which a suppressed reply could nevertheless recreate user
state. These checks are mitigations, not atomic guarantees across a later
await, a handler's database writes, or an already started HTTP request.

Experimental /start envelopes MUST have a valid Telegram Unix message.date
within the most recent 23 hours (with 120 seconds of tolerated future clock
skew). Messages older than this window, without a timestamp, or with an
invalid timestamp are skipped before any experimental handler side effects.
That bounds the replay window strictly below the 24-hour deletion-fence
lifetime. Other interactions, safety messages, and deletion requests do not
use this age filter. The opt-in experimental mode is not suitable for
general message delivery; an outage exceeding 23 hours can drop /start
responses without a user-facing notification.

Tests cover concurrent worker reservations, another Python interpreter,
transaction rollback, expiry, a deletion inserted between reservation and
send initiation, and user-scoped deletion. The offline acceptance
runner also checks that a deleted user's next reservation is blocked.

## What this does NOT guarantee

- A Telegram API request that started **before deletion** may still be
  delivered **after deletion begins**. The bot cannot recall an already
  accepted message; deleting SQLite metadata does not delete Telegram data.
- The new 23-hour timestamp cutoff rejects long-delayed experimental /start
  replays with authentic Telegram timestamps. It does not protect other
  bot commands or prove that timestamps could never be malformed or forged
  by compromised infrastructure. A complete update-epoch protocol is still
  needed if outbound deduplication expands beyond this one command.
- Explicitly opted-in experimental `/start` requests during the fence are
  not automatically resent and may receive no response. This is not suitable
  for general rollout without a user-experience and recovery policy.
- A future new interaction after expiry may legitimately create records
  again. The deletion fence is not a permanent opt-out mechanism.
- The SQLite ledger cannot guarantee exactly-once remote delivery.

Until independent privacy/security/clinical review and actual staging tests,
keep the experimental flag disabled outside controlled tests.
