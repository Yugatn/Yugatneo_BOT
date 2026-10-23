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
