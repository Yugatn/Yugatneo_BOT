# Closed beta: residual risks and acceptance evidence

This is a technical handoff, not an authorization to deploy.

## Verified in automated tests

- SQLite backup integrity and restored report readability
- Duplicate async update delivery does not rerun a completed handler
- A failed handler leaves the update incomplete
- Encrypted reflection receipt prevents duplicate writes after interrupted handling
- Processing lease takeover and retry behaviour
- Quarantine and operator recovery paths

## Remaining risks

1. **External side effects:** message sends and other actions may be repeated if a worker dies after acting but before marking an update done. Add idempotency or an outbox for each non-transactional action.
2. **Live Telegram operations:** run a supervised polling restart with real update redelivery, a single active worker, and no conflicting webhook.
3. **Key recovery:** verify that a restored staging backup can be read using the intended key. A structurally valid backup alone is insufficient.
4. **Privacy:** review access control, retention, backups, deletion propagation, and incident handling.
5. **Content safety:** obtain independent clinical review of crisis responses, age suitability, and psychoeducation.
6. **Operational resilience:** conduct load testing, security testing, incident simulation, and rollback rehearsal.

## Go/no-go

All critical issues require documented owner, evidence, and explicit human sign-off. CI success alone does not approve a closed beta or public release. Never place real personal reports in CI artifacts or issue comments.
