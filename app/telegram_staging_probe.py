"""Read-only Telegram Bot API connectivity probe for local/staging operations.

Run:
    python -m app.telegram_staging_probe
    python -m app.telegram_staging_probe --online

The online mode sends only getMe/getWebhookInfo. It never sends a message,
changes webhook settings, downloads updates or prints bot tokens/URLs.
A successful result is not a public-deployment authorization.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import httpx

from app.core.config import get_settings


def _report(
    *,
    token_configured: bool,
    online_check_performed: bool = False,
    telegram_identity_verified: bool = False,
    webhook_inactive: bool = False,
    check_error: str | None = None,
) -> dict[str, Any]:
    """Only fixed, nonsensitive values ever enter the output."""
    return {
        "token_configured": token_configured,
        "online_check_performed": online_check_performed,
        "telegram_identity_verified": telegram_identity_verified,
        "webhook_inactive": webhook_inactive,
        "polling_preflight_passed": (
            online_check_performed and telegram_identity_verified and webhook_inactive
        ),
        "message_sent": False,
        "public_release_approved": False,
        "check_error": check_error,
    }


def check_offline(token: str | None) -> dict[str, Any]:
    return _report(token_configured=bool(token and token.strip()))


async def _get_result(
    client: httpx.AsyncClient, token: str, method: str
) -> dict[str, Any] | None:
    """Never return raw Telegram errors or raise a URL-bearing HTTPError."""
    try:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/{method}", json={}
        )
        if response.status_code != 200:
            return None
        payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        return None
    result = payload.get("result")
    return result if isinstance(result, dict) else None


async def check_online(
    token: str | None, client: httpx.AsyncClient
) -> dict[str, Any]:
    if not token or not token.strip():
        return _report(
            token_configured=False, online_check_performed=False,
            check_error="missing_bot_token",
        )
    identity = await _get_result(client, token, "getMe")
    if identity is None or identity.get("is_bot") is not True:
        return _report(
            token_configured=True, online_check_performed=True,
            check_error="telegram_identity_check_failed",
        )
    webhook = await _get_result(client, token, "getWebhookInfo")
    if webhook is None or not isinstance(webhook.get("url"), str):
        return _report(
            token_configured=True, online_check_performed=True,
            telegram_identity_verified=True,
            check_error="webhook_check_failed",
        )
    if webhook["url"].strip():
        return _report(
            token_configured=True, online_check_performed=True,
            telegram_identity_verified=True,
            check_error="webhook_active_polling_conflict",
        )
    return _report(
        token_configured=True, online_check_performed=True,
        telegram_identity_verified=True, webhook_inactive=True,
    )


async def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Check Telegram configuration and optional read-only Bot API connectivity."
    )
    parser.add_argument(
        "--online", action="store_true",
        help="Explicitly call getMe and getWebhookInfo. Never sends user messages.",
    )
    args = parser.parse_args()
    token = get_settings().telegram_bot_token
    if args.online:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
            result = await check_online(token, client)
    else:
        result = check_offline(token)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if args.online:
        return 0 if result["polling_preflight_passed"] else 1
    return 0 if result["token_configured"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
