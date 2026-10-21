"""Human verification flow using Cloudflare Turnstile and one-time platform-bound codes.

A CAPTCHA raises the cost of automated abuse; it cannot prove with certainty that a
person is human. Tickets must be created by a verified platform adapter, never from
a client-supplied user ID alone.
"""
import base64
import hashlib
import hmac
import json
import secrets
import time
import sqlite3
from pathlib import Path
import httpx
from app.core.config import get_settings
from app.services.security import issue_human_code


def _db_path() -> str:
    url = get_settings().database_url
    if not url.startswith("sqlite:///"):
        raise RuntimeError("Human gate MVP currently supports SQLite URLs only")
    return url.removeprefix("sqlite:///")


def _connect() -> sqlite3.Connection:
    path = _db_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute("""CREATE TABLE IF NOT EXISTS used_human_tickets (
        nonce_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL
    )""")
    conn.commit()
    return conn


def create_ticket(channel: str, external_user_id: str, signing_secret: str, ttl_seconds: int = 600) -> tuple[str, str]:
    """Call only inside a verified webhook handler, using the identity from the platform."""
    payload = {
        "channel": channel,
        "user_id": external_user_id,
        "exp": int(time.time()) + ttl_seconds,
        "nonce": secrets.token_urlsafe(18),
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(signing_secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return encoded, signature


def _consume_ticket_nonce(nonce: str, expiry: int) -> bool:
    conn = _connect()
    digest = hashlib.sha256(nonce.encode()).hexdigest()
    try:
        conn.execute("DELETE FROM used_human_tickets WHERE expires_at < ?", (int(time.time()),))
        conn.execute("INSERT INTO used_human_tickets(nonce_hash, expires_at) VALUES (?, ?)", (digest, expiry))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()


async def verify_turnstile_and_issue_code(ticket: str, signature: str, token: str, remote_ip: str | None = None) -> str:
    settings = get_settings()
    if not settings.ticket_signing_secret or not settings.turnstile_secret_key:
        raise RuntimeError("Human verification is not configured")
    expected = hmac.new(settings.ticket_signing_secret.encode(), ticket.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Invalid verification ticket")
    try:
        padded = ticket + "=" * (-len(ticket) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
    except Exception as exc:
        raise ValueError("Malformed verification ticket") from exc
    if int(payload.get("exp", 0)) < int(time.time()):
        raise ValueError("Verification ticket expired")
    channel, user_id, nonce = payload.get("channel"), payload.get("user_id"), payload.get("nonce")
    if not all(isinstance(v, str) and v for v in (channel, user_id, nonce)):
        raise ValueError("Invalid ticket identity")
    if channel not in {"telegram", "instagram", "whatsapp", "max"}:
        raise ValueError("Unsupported channel")
    form = {"secret": settings.turnstile_secret_key, "response": token}
    if remote_ip:
        form["remoteip"] = remote_ip
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.post("https://challenges.cloudflare.com/turnstile/v0/siteverify", data=form)
        response.raise_for_status()
        result = response.json()
    if not result.get("success"):
        raise ValueError("Human verification failed")
    if not _consume_ticket_nonce(nonce, int(payload["exp"])):
        raise ValueError("Verification ticket already used")
    return issue_human_code(f"{channel}:{user_id}", ttl_seconds=300)
