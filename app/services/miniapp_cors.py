"""Opt-in CORS for the staging Telegram Mini App coaching API only.

CORS is NOT authentication; every endpoint still verifies Telegram HMAC
initData and user ownership. No wildcard, reflected Origin, credentials or
third-party origins by default.
"""
from __future__ import annotations

from urllib.parse import urlsplit


ALLOWED_METHODS = frozenset({"GET", "POST", "DELETE"})
ALLOWED_HEADERS = frozenset({"authorization", "content-type"})
PREFIX = "/api/v1/miniapp/coaching"


def trusted_origins(raw: str) -> frozenset[str]:
    """Fail closed if configuration is malformed. HTTPS origins only."""
    if not raw or not raw.strip():
        return frozenset()
    values = [item.strip() for item in raw.split(",")]
    result = set()
    for origin in values:
        try:
            parsed = urlsplit(origin)
            if (not origin or parsed.scheme != "https" or not parsed.hostname
                    or parsed.username or parsed.password or parsed.path
                    or parsed.query or parsed.fragment or parsed.netloc.endswith(".")
                    or "*" in origin or parsed.port == 0 or origin !=
                    f"{parsed.scheme}://{parsed.netloc}"):
                return frozenset()
        except ValueError:
            return frozenset()
        result.add(origin)
    return frozenset(result)


def is_coaching_route(path: str) -> bool:
    return path == PREFIX or path.startswith(PREFIX + "/")


def allowed_headers(origin: str, allowed: frozenset[str]) -> dict[str, str] | None:
    if origin not in allowed:
        return None
    return {
        "Access-Control-Allow-Origin": origin,
        "Vary": "Origin",
    }


def preflight_headers(
    origin: str,
    requested_method: str,
    requested_headers: str,
    allowed: frozenset[str],
) -> dict[str, str] | None:
    headers = allowed_headers(origin, allowed)
    if headers is None or requested_method.upper() not in ALLOWED_METHODS:
        return None
    requested = {part.strip().lower() for part in requested_headers.split(",") if part.strip()}
    if not requested.issubset(ALLOWED_HEADERS):
        return None
    return {
        **headers,
        "Access-Control-Allow-Methods": "GET, POST, DELETE",
        "Access-Control-Allow-Headers": "Authorization, Content-Type",
        "Access-Control-Max-Age": "300",
        "Cache-Control": "no-store",
    }
