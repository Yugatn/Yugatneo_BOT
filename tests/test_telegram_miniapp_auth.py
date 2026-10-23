import hashlib
import hmac
import json
from urllib.parse import urlencode
import pytest
from app.services.telegram_miniapp_auth import verify_init_data, InvalidInitData


def signed_data(token="test-token", auth_date=1000, user_id=42):
    values = {"auth_date": str(auth_date), "user": json.dumps({"id": user_id}, separators=(",", ":"))}
    check = "\n".join(f"{k}={v}" for k, v in sorted(values.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def test_valid_signature():
    assert verify_init_data(signed_data(), "test-token", now=1100)["user_id"] == "42"


def test_reject_tampering():
    raw = signed_data().replace("42", "43")
    with pytest.raises(InvalidInitData):
        verify_init_data(raw, "test-token", now=1100)


def test_reject_expired():
    with pytest.raises(InvalidInitData):
        verify_init_data(signed_data(), "test-token", now=6000)


def test_reject_wrong_token():
    with pytest.raises(InvalidInitData):
        verify_init_data(signed_data(), "another-token", now=1100)
