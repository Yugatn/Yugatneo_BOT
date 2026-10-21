from datetime import datetime, timezone
from enum import StrEnum
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Channel(StrEnum):
    TELEGRAM = "telegram"
    INSTAGRAM = "instagram"
    WHATSAPP = "whatsapp"
    MAX = "max"
    WEB = "web"


class IncomingMessage(BaseModel):
    channel: Channel
    external_user_id: str = Field(min_length=1, max_length=256)
    text: str = Field(default="", max_length=12000)
    message_id: str | None = None
    received_at: datetime = Field(default_factory=utc_now)


class OutgoingMessage(BaseModel):
    text: str
    buttons: list[dict[str, str]] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class UserEntitlement(BaseModel):
    user_id: str
    free_questions_used: int = 0
    subscription_active: bool = False
    subscription_expires_at: datetime | None = None


class Question(BaseModel):
    id: str
    category: str
    subcategory: str
    text: str
    purpose: str
    tags: list[str] = Field(default_factory=list)
    risk_level: str = "standard"
