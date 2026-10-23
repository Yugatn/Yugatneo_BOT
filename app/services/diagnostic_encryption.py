"""Optional authenticated encryption for sensitive diagnostic JSON fields.

The key is external to SQLite. Existing plaintext rows remain readable until
rewritten; do not claim that enabling the key migrates or encrypts old rows.
"""
from __future__ import annotations

import os

PREFIX = "fernet:v1:"


class EncryptionConfigurationError(RuntimeError):
    pass


def _fernet():
    key = os.environ.get("YUGATNEO_DATA_ENCRYPTION_KEY", "").strip()
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
        return Fernet(key.encode("ascii"))
    except (ValueError, TypeError, UnicodeError) as exc:
        raise EncryptionConfigurationError("Invalid encryption key") from exc


def encrypt_diagnostic_json(value: str) -> str:
    cipher = _fernet()
    if cipher is None:
        return value
    return PREFIX + cipher.encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_diagnostic_json(value: str) -> str:
    if not value.startswith(PREFIX):
        return value
    cipher = _fernet()
    if cipher is None:
        raise EncryptionConfigurationError(
            "Encrypted diagnostic data requires YUGATNEO_DATA_ENCRYPTION_KEY"
        )
    from cryptography.fernet import InvalidToken
    try:
        return cipher.decrypt(value[len(PREFIX):].encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeError, ValueError) as exc:
        raise EncryptionConfigurationError(
            "Unable to decrypt diagnostic data: wrong key or corrupt ciphertext"
        ) from exc
