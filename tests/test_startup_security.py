import pytest
from cryptography.fernet import Fernet

from app.services.diagnostic_encryption import EncryptionConfigurationError
from app.services.startup_security import validate_encryption_startup


def test_production_rejects_missing_key(monkeypatch):
    monkeypatch.setenv("YUGATNEO_ENV", "production")
    monkeypatch.delenv("YUGATNEO_DATA_ENCRYPTION_KEY", raising=False)
    with pytest.raises(EncryptionConfigurationError, match="Production requires"):
        validate_encryption_startup()


def test_production_rejects_invalid_key(monkeypatch):
    monkeypatch.setenv("YUGATNEO_ENV", "production")
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", "not-a-valid-key")
    with pytest.raises(EncryptionConfigurationError, match="Invalid encryption key"):
        validate_encryption_startup()


def test_production_accepts_valid_key(monkeypatch):
    monkeypatch.setenv("YUGATNEO_ENV", "production")
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    validate_encryption_startup()


def test_development_without_key_is_supported(monkeypatch):
    monkeypatch.setenv("YUGATNEO_ENV", "development")
    monkeypatch.delenv("YUGATNEO_DATA_ENCRYPTION_KEY", raising=False)
    validate_encryption_startup()


def test_unrecognized_mode_is_rejected(monkeypatch):
    monkeypatch.setenv("YUGATNEO_ENV", "prodution")
    with pytest.raises(EncryptionConfigurationError, match="Invalid YUGATNEO_ENV"):
        validate_encryption_startup()
