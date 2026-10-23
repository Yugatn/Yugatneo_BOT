import json
import sqlite3

import pytest
from cryptography.fernet import Fernet

from app.services import diagnostic_flow
from app.services.diagnostic_encryption import (
    PREFIX, EncryptionConfigurationError, encrypt_diagnostic_json,
    decrypt_diagnostic_json,
)


def test_encryption_round_trip_and_no_plaintext(monkeypatch):
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    value = '{"private":"личная рефлексия"}'
    ciphertext = encrypt_diagnostic_json(value)
    assert ciphertext.startswith(PREFIX)
    assert "личная рефлексия" not in ciphertext
    assert decrypt_diagnostic_json(ciphertext) == value


def test_missing_or_wrong_key_fails_closed(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", key)
    ciphertext = encrypt_diagnostic_json('{"goal":"health"}')
    monkeypatch.delenv("YUGATNEO_DATA_ENCRYPTION_KEY")
    with pytest.raises(EncryptionConfigurationError):
        decrypt_diagnostic_json(ciphertext)
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    with pytest.raises(EncryptionConfigurationError):
        decrypt_diagnostic_json(ciphertext)


def test_existing_plaintext_remains_readable(monkeypatch):
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    assert decrypt_diagnostic_json('{"legacy":true}') == '{"legacy":true}'


def test_diagnostic_store_encrypts_new_answers(tmp_path, monkeypatch):
    path = tmp_path / "diagnostic.sqlite"
    monkeypatch.setattr(diagnostic_flow, "_db_path", lambda: str(path))
    monkeypatch.setenv("YUGATNEO_DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    diagnostic_flow._write("telegram", "u1", 0, {"goal": "private goal"})
    with sqlite3.connect(path) as conn:
        stored = conn.execute("SELECT answers_json FROM diagnostic_sessions").fetchone()[0]
    assert stored.startswith(PREFIX)
    assert "private goal" not in stored
    assert diagnostic_flow._read("telegram", "u1")["answers"]["goal"] == "private goal"
