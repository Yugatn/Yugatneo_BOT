"""Signed Telegram Mini App initData verification.

Use the bot token only on the backend. Never trust a user ID from browser JSON.
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


class InvalidInitData(ValueError):
    pass


def verify_init_data(raw: str, bot_token: str, *, now: int | None = None,
                     max_age_seconds: int = 3600) -> dict:
    if not raw or not bot_token or len(raw) > 16384:
        raise InvalidInitData("missing or oversized initData")
    pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True)
    fields = dict(pairs)
    if len(fields) != len(pairs) or "hash" not in fields:
        raise InvalidInitData("invalid initData fields")
    supplied = fields.pop("hash")
    if len(supplied) != 64:
        raise InvalidInitData("invalid signature length")
    check = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, supplied):
        raise InvalidInitData("signature mismatch")
    try:
        auth_date = int(fields["auth_date"])
        user = json.loads(fields["user"])
        user_id = user["id"]
        if type(user_id) is not int or user_id <= 0:
            raise ValueError()
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise InvalidInitData("missing valid user/auth_date") from exc
    current = int(time.time()) if now is None else now
    if max_age_seconds <= 0 or auth_date > current + 30 or current - auth_date > max_age_seconds:
        raise InvalidInitData("expired initData")
    return {"user_id": str(user_id), "auth_date": auth_date}
