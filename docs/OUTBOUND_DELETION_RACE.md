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
between reservation and send initiation. This is a mitigation, not an
atomic guarantee across a later await or an already started HTTP request.

Tests cover concurrent worker reservations, another Python interpreter,
transaction rollback, expiry, a deletion inserted between reservation and
send initiation, and user-scoped deletion. The offline acceptance
runner also checks that a deleted user's next reservation is blocked.

## What this does NOT guarantee

- A Telegram API request that started **before deletion** may still be
  delivered **after deletion begins**. The bot cannot recall an already
  accepted message; deleting SQLite metadata does not delete Telegram data.
- A message queued for more than 24 hours could be processed after the fence
  has expired. Long-delayed replays need a further update-epoch protocol.
- Explicitly opted-in experimental `/start` requests during the fence are
  not automatically resent and may receive no response. This is not suitable
  for general rollout without a user-experience and recovery policy.
- A future new interaction after expiry may legitimately create records
  again. The deletion fence is not a permanent opt-out mechanism.
- The SQLite ledger cannot guarantee exactly-once remote delivery.

Until independent privacy/security/clinical review and actual staging tests,
keep the experimental flag disabled outside controlled tests.
