# Outbound delivery incident runbook

This runbook applies to the metadata-only outbound ledger in
`app/services/outbound_delivery.py`. The adapter is opt-in and is **not**
connected to the production Telegram polling loop.

## Meaning of states

- `pending`: legacy ledger entry; not proof of a network request.
- `ambiguous`: a reservation exists, but delivery is **not verified**.
  This can include a crash before the network call, a timeout after Telegram
  accepted the message, or a process crash before the success receipt.
- `sent`: the adapter observed a successful API response and recorded it.
  It is not evidence that the recipient read the message.

## Response to an ambiguous delivery

1. Do not automatically replay the event. Telegram `sendMessage` does not
   support a general client-provided idempotency key.
2. Inspect only aggregate counts via `delivery_counts`; do not dump raw
   message bodies, credentials, or psychological reflections into logs.
3. Determine whether the message is time-critical or safety-related.
   An uncertain safety response must be escalated to a trained human operator
   under a separately approved protocol; do not silently suppress it.
4. Before any manual resend, check the user's consent, the conversation
   context and whether a duplicate could cause harm.
5. Record the decision and rationale in an access-controlled audit system
   with defined retention. Such an audit system is **not implemented yet**.
6. Respect data deletion requests; user-scoped outbound metadata deletion
   is **not implemented yet**, so production integration is prohibited.

## Release conditions

Do not enable the adapter in the polling runner until stable event keys,
user-scoped deletion, operator reconciliation, security review, and safety
response handling are implemented and tested. A green CI build alone is
insufficient for public release.
