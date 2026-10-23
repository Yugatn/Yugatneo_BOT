# Controlled beta release checklist

This checklist does not grant permission to launch. Keep the public bot offline
until responsible human reviewers approve the outstanding safety work.

## Technical checks

- [ ] GitHub Actions tests pass on supported Python versions
- [ ] Run `environment_preflight(db_path)` on the target host
- [ ] Verify valid encryption configuration with startup checks
- [ ] Run `count_unreadable_reports(db_path)` on a protected staging copy; require `unreadable == 0`
- [ ] After restoring a backup, repeat report readability verification with the intended key
- [ ] Verify backup, restore, and scoped personal-data deletion on staging
- [ ] Test Telegram polling restart with an unacknowledged update
- [ ] Test quarantine, explicit operator recovery, and audit recording
- [ ] Confirm a single active polling worker and no active webhook
- [ ] Confirm access controls, secret rotation and incident contact

## Independent reviews

- [ ] Clinical and psychoeducational content review
- [ ] Privacy and data protection assessment
- [ ] Security penetration test
- [ ] Load, crash and recovery exercise
- [ ] Incident response exercise
- [ ] Consent and age-appropriate experience review

## Pilot safeguards

- [ ] Recruit a small consent-based adult cohort initially
- [ ] Publish limits: not diagnosis, emergency care or crisis intervention
- [ ] Verify crisis response and human escalation information
- [ ] Provide working export/deletion and feedback channels
- [ ] Define monitoring, retention, stop conditions and rollback owner

The `environment_preflight` helper checks configuration presence, Fernet key
format and filesystem access. It does not verify whether the key can decrypt
existing records, Telegram connectivity, clinical safety, or production security.
A successful CI run is not authorization to deploy.

## Offline restore acceptance

Run the existing `verify_sqlite_backup` check against a restored staging copy before attempting to read reports. Reject any result where `passed` is false. Next run `count_unreadable_reports` with the intended encryption key and require `unreadable == 0`. An empty report table is not evidence that a key is correct; retain an encrypted test fixture in staging for positive verification. Never print summaries or identifiers in diagnostics. A passed integrity check does not imply readable encrypted data. Keep the restored database isolated from production and do not overwrite the source.

## Duplicate delivery acceptance

The asynchronous dispatcher must invoke a handler only once for an already completed update. A handler exception must leave the update uncompleted so it can be retried after its processing lease expires. Confirm both behaviours in CI; also conduct a separate end-to-end Telegram polling restart exercise before beta approval. Exactly-once side effects are not guaranteed for arbitrary handlers if the process crashes after side effects but before marking an update complete.
