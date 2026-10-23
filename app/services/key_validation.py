"""Offline validation of Fernet encryption configuration."""
from cryptography.fernet import Fernet


def encryption_key_is_valid(value):
    if not isinstance(value, str) or not value:
        return False
    try:
        Fernet(value.encode("ascii"))
    except (ValueError, TypeError, UnicodeError):
        return False
    return True
