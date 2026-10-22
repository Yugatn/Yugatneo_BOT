"""Small Telegram Bot API CLI. Reads TELEGRAM_BOT_TOKEN via project settings.

Usage:
    python -m app.telegram_cli me
    python -m app.telegram_cli updates
    python -m app.telegram_cli send CHAT_ID "message"
Never pass a token as a command-line argument.
"""
import argparse
import asyncio
import json
import sys

import httpx
from app.core.config import get_settings


async def call(method: str, payload: dict | None = None):
    token = get_settings().telegram_bot_token
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing from the local environment")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/{method}",
            json=payload or {},
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram rejected {method}: {data.get('description', 'unknown error')}")
        return data["result"]


async def main():
    parser = argparse.ArgumentParser(description="Telegram Bot API terminal client")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("me")
    sub.add_parser("updates")
    send = sub.add_parser("send")
    send.add_argument("chat_id", type=int)
    send.add_argument("message")
    args = parser.parse_args()

    if args.action == "me":
        result = await call("getMe")
    elif args.action == "updates":
        result = await call("getUpdates", {"timeout": 0, "limit": 10})
    else:
        result = await call("sendMessage", {"chat_id": args.chat_id, "text": args.message})
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (RuntimeError, httpx.HTTPError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        raise SystemExit(1)
