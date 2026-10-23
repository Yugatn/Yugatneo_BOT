# Offline-first execution plan

The next milestones require no Telegram bot token, server, domain, webhook,
public database, or production user.

## P0 — finish locally and in GitHub Actions

- [x] Offline fake Telegram transport with failure injection
- [x] Regression tests for successful send and lost acknowledgement
- [x] Scoped outbound receipts and account deletion tests
- [x] Tests for concurrent reservations and cancelled requests
- [x] Explicit opt-in experimental /start integration, prohibited in production
- [x] Test failure before remote acceptance and repeated delivery
- [x] Test malformed updates and boundary cases for the /start guard
- [x] Check report encryption and restore with a synthetic staging fixture
- [x] Check outbound SQLite schema initialization on empty and existing databases
- [x] Test Telegram API error redaction for failed HTTP and malformed responses; full audit pending
- [x] Exercise restart, quarantine and operator recovery offline (existing CI regression tests)
- [x] Run scheduled dependency vulnerability audit with remediation verified in CI
- [x] Run Bandit medium/high-confidence application source scan; remediate three findings
- [x] Produce operator runbook with measurable pass/fail acceptance
- [x] Block new experimental outbound reservations after deletion across processes for 24 hours; test concurrency and expiry
- [x] Reject stale or timestamp-less experimental /start updates after 23 hours
- [x] Check active deletion fence before experimental /start handler state writes
- [ ] Define policy for already in-flight network requests and post-deletion state writes in other flows
- [ ] Review delayed-update policy before enabling additional outbound commands
- [x] Document internal privacy/security risk inventory and reproducible evidence
- [ ] Obtain independent security, privacy and clinical reviews (human sign-off)

The synthetic acceptance runner is now part of Tests CI on Python 3.11 and 3.12.
A scheduled/on-demand dependency security audit is also active. The initial
scan identified vulnerable older pytest/cryptography constraints; these were
raised and the audit passed on commit f35e558. A Bandit source scan now runs on application code changes; its initial three
medium-confidence findings were addressed by a localhost-only default bind
and literal, allowlisted SQL statements. These automated checks still do not
replace a human security assessment.
Remaining P0 risks include already in-flight sends, non-atomic handler writes,
deletion-fence personal-data retention, and independent security review.
Experimental /start replays older than 23 hours are now suppressed when the
flag is enabled, but this does not extend to other commands. A green offline
test does not close these risks.

## P1 — infrastructure-dependent tasks (after P0)

- [ ] Create isolated staging Telegram bot credentials
- [ ] Configure one polling worker on a protected host
- [ ] Verify Telegram API integration with test accounts
- [ ] Run staging backup/restore and key-rotation drill
- [ ] Set up monitoring, incident contact and rollback
- [ ] Conduct independent privacy, security and clinical reviews
- [ ] Authorize limited adult beta only after documented sign-off

## P2 — later product development

- [ ] Improve UX and accessibility across supported languages
- [ ] Improve coaching and career guidance with sourced content
- [ ] Add user-visible feedback and export controls
- [ ] Optimize latency, operational cost and maintenance

## Execution policy

Finish and validate P0 work before requesting hosting access. The fake
transport does not prove Telegram's real network behavior. Automated tests
are not a substitute for independent human safety review. Never commit
credentials or actual user conversations.
