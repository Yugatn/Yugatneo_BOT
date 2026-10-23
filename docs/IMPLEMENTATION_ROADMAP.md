# Yugatneo BOT — prioritized delivery roadmap

Status: engineering plan, not an authorization to launch. Baseline: both GitHub
Actions suites passed at commit 419abf7. Percentages are estimates, not
independent release certifications.

| Priority | Phase | Deliverable / acceptance evidence | State |
|---|---|---|---|
| P0 | Safety and transport correctness | Isolate emergency/deletion flows; opt-in /start delivery; simulate timeout, cancellation, concurrency and deletion races; CI green | In progress |
| P0 | Outbound deletion consistency | Prevent a new outbound reservation after account deletion has begun; define deletion/active-send synchronization; verify scoped deletion | Not started |
| P0 | Deployment safety | Single worker, webhook exclusion, secrets, staging key readability, backup/restore, operator rollback | Partially implemented; staging proof pending |
| P1 | Controlled Telegram integration | Staging bot token; verify real API acknowledgement and retry behavior; flag off by default; no real users | Not started |
| P1 | Quality and privacy | Independent clinical, age/consent, privacy, security reviews; retention and human escalation | Pending human review |
| P1 | Closed adult beta | Small opt-in cohort, incident contact, explicit stop criteria, telemetry without sensitive content | Blocked on reviews |
| P2 | Product capabilities | Improve coaching, balance wheel, career pathways, multilingual usability and accessible UX | After P0/P1 |
| P2 | Operations | Metrics, runbooks, backup drills, performance budgets and staged rollouts | Planned |
| P3 | Public release | Signed approvals, measured stability, legal compliance and rollback readiness | Not authorized |

## Immediate execution order

1. P0: Add regression tests for polling integration and privacy boundaries.
2. P0: Close the deletion/in-flight reservation race, not just the
   deletion/confirmation race. Do not equate local deletion with recall of
   a message already accepted by Telegram.
3. P0: Exercise cancellation, crash windows, duplicate update delivery,
   and sensitive-message bypass. Require both CI suites to pass.
4. P0: Create a repeatable staging acceptance checklist with evidence fields
   for operator, date, environment, test result, and rollback decision.
5. P1: Test with an isolated Telegram bot in staging only after P0 evidence.
6. P1: Obtain external human approvals before inviting beta users.

## Non-negotiable release gates

- The experimental flag is OFF by default.
- No claims of guaranteed exactly-once Telegram delivery.
- Crisis messages and account deletion must not be suppressed by deduplication.
- Psychological reports and credentials must not enter outbound logs.
- Uncertain delivery is never silently described as confirmed.
- A passing automated test suite does not substitute for a clinical,
  security or privacy assessment.

## Progress accounting

Track independently: code implemented, automated tests green, staging
verification, and external approvals. Do not use a single engineering
percentage as a public-release readiness measure.
