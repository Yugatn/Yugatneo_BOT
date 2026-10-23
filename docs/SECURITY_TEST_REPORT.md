# Threat model and defensive test report

## Scope
Offline adversarial tests for the Telegram polling implementation. **No live penetration test, external scan or production security certification has been performed.**

## Tested scenarios
- Token leakage: simulated Telegram HTTP 403; raised error must not contain the bot token or request URL.
- SQL injection: hostile Telegram user ID must not alter another user's SQLite security record.
- Spam: verified users must still be subject to the per-user message limit.
- Privacy: group messages must be ignored; oversized private messages rejected before database access.

Run locally with `python -m pytest -q tests/test_adversarial_security.py`. Full CI runs these tests on push.

## Risk register
| Risk | Current status | Required before public launch |
|---|---|---|
| Telegram token exposed by exception messages | Sanitized in polling API wrapper | Verify log aggregation and rotate any potentially exposed token |
| SQL injection | Parameterized queries in tested security path | Audit all remaining database queries |
| Per-user spam | SQLite per-user limit and CAPTCHA | Add global rate limit and API spending budget |
| Public disclosure of reflections | Group chats ignored; Telegraph disabled | Review backups, logs, exports and data retention |
| Sensitive SQLite data at rest | **Not encrypted** | Encrypted volume or database encryption, restricted file permissions and encrypted backups |
| Unverified user identity | Telegram user ID is trusted from Bot API updates | Secure bot token and restrict server access |
| Data deletion | Several local tables deleted | Verify all data stores, diagnostics, backups and deletion lifecycle |
| Prompt injection via user text | **Not fully tested** | Isolate instructions, limit tool privileges, add injection tests |
| DDoS and multi-account abuse | **Not protected** | Hosting/network controls and shared quotas |

## Release gate
Do not describe the bot as secure or production-ready until CI is green, live Telegram smoke tests pass, secrets are configured safely, and a human reviews data retention, incident response and privacy compliance.
