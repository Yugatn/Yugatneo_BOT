"""Fail-closed production preflight for encryption settings.

The gate is an operational safeguard, not proof that every SQLite field is encrypted.
"""
from __future__ import annotations

import os

from app.services.diagnostic_encryption import EncryptionConfigurationError


def validate_encryption_startup() -> None:
    mode = os.environ.get("YUGATNEO_ENV", "development").strip().lower()
    if mode not in {"development", "test", "production"}:
        raise EncryptionConfigurationError("Invalid YUGATNEO_ENV setting")
    key = os.environ.get("YUGATNEO_DATA_ENCRYPTION_KEY", "").strip()
    if mode == "production" and not key:
        raise EncryptionConfigurationError(
            "Production requires YUGATNEO_DATA_ENCRYPTION_KEY"
        )
    if key:
        try:
            from cryptography.fernet import Fernet
            Fernet(key.encode("ascii"))
        except (ValueError, TypeError, UnicodeError) as exc:
            raise EncryptionConfigurationError("Invalid encryption key") from exc
