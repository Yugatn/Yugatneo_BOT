"""Telegram Bot API adapter helpers.

The webhook route and outbound send call should be added after the bot token,
public HTTPS URL and deployment environment are configured.
"""
from app.core.models import Channel, IncomingMessage


def normalize_telegram_update(update: dict) -> IncomingMessage | None:
    message = update.get("message") or update.get("edited_message")
    if not message or not message.get("from"):
        return None
    text = message.get("text") or message.get("caption") or ""
    return IncomingMessage(
        channel=Channel.TELEGRAM,
        external_user_id=str(message["from"]["id"]),
        text=text,
        message_id=str(message.get("message_id", "")) or None,
    )
