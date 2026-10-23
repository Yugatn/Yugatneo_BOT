"""Check privacy invariants for opt-in reflection data.

Only counts and boolean status are returned; never include identifiers,
encrypted payloads, message text, or personal records in audit reports.
"""
from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from app.services.personal_data import PERSONAL_TABLES


@dataclass(frozen=True)
class PrivacyAudit:
    passed: bool
    findings: tuple[str, ...]
    checked_tables: int


def audit_reflection_storage(db_path) -> PrivacyAudit:
    issues: list[str] = []
    checked = 0
    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if "guided_reflection_reports" in tables:
            checked += 1
            columns = {
                row[1] for row in conn.execute(
                    "PRAGMA table_info(guided_reflection_reports)"
                )
            }
            if not {"telegram_user_id", "encrypted_summary"}.issubset(columns):
                issues.append("reflection_schema_invalid")
            else:
                rows = conn.execute(
                    "SELECT encrypted_summary FROM guided_reflection_reports"
                )
                for (payload,) in rows:
                    if not isinstance(payload, str) or not payload.startswith("fernet:v1:"):
                        issues.append("unencrypted_reflection_detected")
                        break
        if "guided_reflection_reports" not in PERSONAL_TABLES:
            issues.append("reflection_missing_from_deletion_allowlist")
    return PrivacyAudit(not issues, tuple(issues), checked)


def audit_report_decryption(db_path):
    """Count records unreadable with the configured key, without returning data."""
    from app.services.diagnostic_encryption import (
        decrypt_diagnostic_json, EncryptionConfigurationError, PREFIX,
    )
    checked = 0
    failures = 0
    with sqlite3.connect(db_path) as conn:
        present = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='guided_reflection_reports'"
        ).fetchone()
        if not present:
            return {"checked": 0, "failures": 0, "passed": True}
        for (payload,) in conn.execute(
            "SELECT encrypted_summary FROM guided_reflection_reports"
        ):
            checked += 1
            try:
                if not isinstance(payload, str) or not payload.startswith(PREFIX):
                    failures += 1
                else:
                    decrypt_diagnostic_json(payload)
            except EncryptionConfigurationError:
                failures += 1
    return {"checked": checked, "failures": failures, "passed": failures == 0}
