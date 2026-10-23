# Closed beta controlled rollout protocol

**Status:** proposed procedure; not authorization to deploy.

## Phase 0 — offline verification

1. Pin a reviewed Git commit and capture passing CI run identifiers.
2. On a disposable staging environment, run `environment_preflight(db_path)`.
   Inspect only boolean results; never include tokens or encryption keys in logs.
3. Restore a verified encrypted backup in staging, confirm that existing
   records decrypt with the configured key, then test scoped deletion.
4. Run the quarantine integration tests and crash-recovery exercises.
5. Confirm a single polling worker, no active webhook and documented rollback.

## Phase 1 — human authorization

Require written sign-off from clinical-content, privacy and security reviewers.
Assign an incident owner and an operator responsible for pausing the pilot.
Confirm retention, data-subject requests, consent and age gates. Record decisions
outside the bot database with access controls.

## Phase 2 — limited adult pilot

Start only with explicitly consenting adult testers. No unsolicited invitations.
Use test accounts and synthetic data before any real personal reflections.
Watch aggregate error counts, failed handlers, quarantine counts and complaints.
Avoid raw chat content in monitoring.

## Stop conditions

Immediately pause the pilot for a suspected personal-data exposure, repeated
unrecoverable failures, broken deletion or encryption, unsafe crisis guidance,
or evidence that age/consent controls are bypassed. Preserve restricted audit
records and follow the incident response procedure.

## Exit criteria

Pilot results and independent reviews must be documented. Successful unit
tests and a 100% engineering progress estimate alone do not authorize a
public release.
