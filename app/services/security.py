"""Security primitives for the MVP."""
import hashlib
import hmac
import secrets
import sqlite3
import time
from pathlib import Path
from app.core.config import get_settings


def _db_path() -> str:
    url = get_settings().database_url
    if not url.startswith("sqlite:///"):
        raise RuntimeError("MVP security store currently supports SQLite URLs only")
    return url.removeprefix("sqlite:///")


def _connect() -> sqlite3.Connection:
    path = _db_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute("""CREATE TABLE IF NOT EXISTS rate_events (
        subject_key TEXT NOT NULL, created_at INTEGER NOT NULL
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rate_events ON rate_events(subject_key, created_at)")
    conn.execute("""CREATE TABLE IF NOT EXISTS human_verifications (
        code_hash TEXT PRIMARY KEY, subject_key TEXT NOT NULL, expires_at INTEGER NOT NULL,
        used_at INTEGER
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS verified_humans (
        subject_key TEXT PRIMARY KEY, verified_at INTEGER NOT NULL
    )""")
    conn.commit()
    return conn


def allow_request(subject: str, *, limit: int = 12, window_seconds: int = 60) -> bool:
    """SQLite fixed-window limiter; production needs edge protection and shared storage."""
    now = int(time.time())
    key = hashlib.sha256(subject.encode("utf-8")).hexdigest()
    conn = _connect()
    try:
        conn.execute("DELETE FROM rate_events WHERE created_at < ?", (now - window_seconds,))
        count = conn.execute(
            "SELECT COUNT(*) FROM rate_events WHERE subject_key=? AND created_at>?",
            (key, now - window_seconds),
        ).fetchone()[0]
        if count >= limit:
            conn.commit()
            return False
        conn.execute("INSERT INTO rate_events(subject_key, created_at) VALUES (?, ?)", (key, now))
        conn.commit()
        return True
    finally:
        conn.close()


def issue_human_code(subject: str, *, ttl_seconds: int = 300) -> str:
    """Create a short-lived one-time code after a successful CAPTCHA callback."""
    code = secrets.token_urlsafe(9)
    digest = hashlib.sha256(code.encode()).hexdigest()
    subject_hash = hashlib.sha256(subject.encode()).hexdigest()
    conn = _connect()
    try:
        conn.execute("DELETE FROM human_verifications WHERE expires_at < ?", (int(time.time()),))
        conn.execute(
            "INSERT INTO human_verifications(code_hash, subject_key, expires_at) VALUES (?, ?, ?)",
            (digest, subject_hash, int(time.time()) + ttl_seconds),
        )
        conn.commit()
    finally:
        conn.close()
    return code


def consume_human_code(subject: str, code: str) -> bool:
    """Atomically consume a one-time code bound to one platform identity."""
    digest = hashlib.sha256(code.encode()).hexdigest()
    subject_hash = hashlib.sha256(subject.encode()).hexdigest()
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT subject_key, expires_at, used_at FROM human_verifications WHERE code_hash=?",
            (digest,),
        ).fetchone()
        if not row or row[0] != subject_hash or row[1] < int(time.time()) or row[2] is not None:
            conn.rollback()
            return False
        conn.execute("UPDATE human_verifications SET used_at=? WHERE code_hash=?", (int(time.time()), digest))
        conn.execute(
            "INSERT INTO verified_humans(subject_key, verified_at) VALUES (?, ?) "
            "ON CONFLICT(subject_key) DO UPDATE SET verified_at=excluded.verified_at",
            (subject_hash, int(time.time())),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def is_human_verified(subject: str, *, max_age_seconds: int = 60 * 60 * 24 * 30) -> bool:
    subject_hash = hashlib.sha256(subject.encode()).hexdigest()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT verified_at FROM verified_humans WHERE subject_key=?", (subject_hash,)
        ).fetchone()
        return bool(row and int(row[0]) >= int(time.time()) - max_age_seconds)
    finally:
        conn.close()


def verify_signed_ticket(payload: str, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
