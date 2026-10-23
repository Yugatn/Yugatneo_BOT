# Telegram outbound delivery: crash-safety design

## Current behaviour

The inbound update ledger avoids rerunning completed updates. Encrypted guided
report writes have a transactional receipt. Outbound `sendMessage` calls,
however, are not exactly-once: a process can stop after Telegram accepts a
message but before the update ledger records completion.

## Proposed outbox protocol

1. Assign a stable event key from the incoming Telegram update ID, response
   sequence number, and action type. Avoid storing raw user text in logs.
2. Store the intended action and its state in an encrypted, access-controlled
   outbox. Define explicit retention and scoped deletion.
3. A single worker claims a pending action with a bounded lease.
4. Send through Telegram and record the resulting message ID.
5. If Telegram accepted the send but the acknowledgement was lost, delivery is
   ambiguous. Do **not** claim exactly-once semantics: Telegram Bot API
   `sendMessage` does not expose a general client idempotency key.
6. For ambiguous outcomes, prefer explicit reconciliation or a policy that
   tolerates rare duplicates, rather than silent loss of critical safety text.
7. Make outgoing notifications distinguishable from user-initiated responses.
   Add bounded retries, backoff, quarantine, and operator audit.

## Acceptance tests

- Duplicate inbound update never creates a second committed outbox action.
- A crash before sending allows a safe retry.
- A crash after sending but before recording acknowledgement is reported as
  ambiguous, never falsely marked delivered.
- Concurrent workers cannot claim the same active lease.
- User deletion removes scoped outbox content and receipts.
- No plaintext psychological report appears in the outbox, logs, or CI output.

Do not enable outbound queuing for personal reports until privacy and recovery
reviews have passed.


## Implementation status (October 2026)

The current `app/services/outbound_delivery.py` is a **metadata-only**
ledger, not a durable payload outbox. It supports atomic reservation,
confirmed-success recording, aggregate counts, and an opt-in asynchronous
transport wrapper. It is **not wired to the polling runner**.

Reservation is recorded as `ambiguous` before the network call. This
conservatively suppresses duplicate automatic sends after a crash, but
also means a crash *before* the network call may leave an unsent message
requiring operator review. This differs from the proposed full outbox
protocol's recoverable pre-send state. There is no automatic reconciliation
or delivery guarantee yet.

The tests cover concurrent reservation, acknowledgement loss and
pre-send failure. The next integration must define stable event keys,
operator reconciliation, retention/deletion and a user-visible policy
for messages whose delivery is uncertain. In particular, urgent safety
responses must not be silently discarded because of an ambiguous receipt.
