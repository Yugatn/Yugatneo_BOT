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
