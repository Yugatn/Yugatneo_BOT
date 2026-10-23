# Database maintenance checklist

Before rotating encryption keys or restoring user reports:

1. Stop Telegram bot writers and other processes accessing the SQLite database.
2. Create a consistent SQLite backup using the SQLite backup API, not a file copy while writes are active.
3. Verify the backup with `verify_sqlite_backup(path)` from `app.services.backup_integrity`.
4. Preserve the current encryption key in secure external storage. A valid SQLite file does not guarantee that its encrypted data is decryptable.
5. Run the reflection-only key rotation in dry-run mode. Investigate any unreadable records before proceeding.
6. After explicit operator approval, perform the transaction and verify encrypted report readback with the new key.
7. Resume writes only after verifying database health and recovery readiness.

Current limitation: the rotation implementation only handles guided reflection reports. Do not change the shared encryption key for other tables using this procedure alone.

Never include plaintext reports, database files, or secret keys in GitHub issues, CI logs or generated reports.
