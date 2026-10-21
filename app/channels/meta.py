"""Shared normalization helpers for Instagram and WhatsApp webhooks.

Instagram Messaging API and WhatsApp Cloud API have different payload shapes.
Keep separate verified webhook handlers and map both into IncomingMessage.
Do not trust unverified webhook payloads or accept arbitrary outbound recipients.
"""
from app.core.models import Channel, IncomingMessage


def normalize_instagram_text(*, sender_id: str, text: str, message_id: str | None = None) -> IncomingMessage:
    return IncomingMessage(
        channel=Channel.INSTAGRAM,
        external_user_id=sender_id,
        text=text,
        message_id=message_id,
    )


def normalize_whatsapp_text(*, sender_id: str, text: str, message_id: str | None = None) -> IncomingMessage:
    return IncomingMessage(
        channel=Channel.WHATSAPP,
        external_user_id=sender_id,
        text=text,
        message_id=message_id,
    )
