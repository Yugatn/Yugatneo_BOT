# P0 internal security and privacy review (NOT an independent audit)

Reviewed scope: experimental Telegram `/start` delivery, scoped deletion,
SQLite receipts and backup/readability evidence. This register supports an
independent assessment; it does **not** authorize deployment or make any
claim of legal compliance.

## Assets and trust boundaries

| Asset | Where it exists | Boundary and protection |
|---|---|---|
| Telegram user identifier | User-scoped SQLite tables | Personal data; direct identifier |
| Guided reflection summary | `guided_reflection_reports` | Fernet-encrypted at rest; key must be kept outside Git |
| Outbound event metadata | `user_outbound_delivery` | No message body; identifier and state only |
| Temporary deletion suppression | `outbound_deletion_fence` | User identifier + expiry; 24h logical block; cleanup on startup/hourly |
| Outgoing Telegram text | Bot memory and Telegram API | Provider may retain copies outside local deletion scope |
| SQLite backups | Isolated operator-controlled files | Must be access-controlled, encrypted and retention-managed |

## Residual risks and required owners

| Risk | Severity | Current automated evidence | Open decision |
|---|---|---|---|
| Outbound API request may finish after user deletion | High | In-flight deletion regression; no local receipt recreation | Define network cancellation/acknowledgement semantics and acceptable operator response |
| Deletion fence retains direct Telegram user ID | High (privacy) | 24h expiry and startup/hourly cleanup | Independent assessment of legal basis, notice, necessity, retention and physical removal on offline hosts |
| Old inbound update may be replayed after 24h fence expiry | High | Lease/quarantine tests; limited fence | Add update-epoch barrier or formally prohibit long-delayed replay |
| Confirmed Telegram delivery cannot be recalled from provider | High | Response and deletion disclosure | Review third-party retention and user disclosures |
| Outbound send after lost acknowledgement is uncertain | Medium/High | Offline failure injection; ambiguous reservation never auto-retried | Operator reconciliation and human-visible status |
| Experimental `/start` may silently suppress a legitimate retry | Medium | Deduplication tests | Build explicit recovery UX before widening the feature |
| Production environment accidentally enables experiment | Medium | Env guard rejects `production` and unknown stages | Keep flag OFF outside controlled staging |
| Encrypted data restore fails with wrong key | High | Synthetic restore tests and wrong-key tests | Staging key custody and backup/rotation exercise |
| Clinical or crisis-response quality | High | Static tests only | Independent qualified clinical review; human escalation |
| Data may persist in logs/external services/backups | High | API error redaction, no report bodies in outbound ledger | Review retention, log sinks, provider controls and backups |

## Existing automated evidence

- Python 3.11/3.12 unit tests, including no-network offline acceptance.
- GitHub Actions dependency audit and Bandit medium/high source scan.
- In-flight send, deletion receipt, concurrent threads and separate-process
  regression tests.
- Fernet synthetic report backup, restore, readability and scoped deletion.

## Deployment decision

**NO GO for public or real-user closed beta.** The experimental transport is
allowed only in development, test and isolated staging when explicitly enabled.
Neither automated testing nor this internal assessment replaces human sign-off.

Required signatures before beta: accountable operator, qualified clinical
reviewer, independent security reviewer and privacy/data-protection reviewer.
All evidence must reference the tested commit SHA, date and environment.
