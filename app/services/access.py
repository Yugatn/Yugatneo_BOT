from datetime import datetime, timezone
from app.core.models import UserEntitlement


class AccessDecision:
    def __init__(self, allowed: bool, reason: str, remaining_free: int = 0):
        self.allowed = allowed
        self.reason = reason
        self.remaining_free = remaining_free


def has_active_subscription(entitlement: UserEntitlement) -> bool:
    if not entitlement.subscription_active:
        return False
    expiry = entitlement.subscription_expires_at
    return expiry is None or expiry > datetime.now(timezone.utc)


def can_access_question(entitlement: UserEntitlement, free_limit: int = 7) -> AccessDecision:
    if has_active_subscription(entitlement):
        return AccessDecision(True, "active_subscription", free_limit)
    remaining = max(0, free_limit - entitlement.free_questions_used)
    if remaining > 0:
        return AccessDecision(True, "free_question_available", remaining)
    return AccessDecision(False, "subscription_required", 0)


def record_question_use(entitlement: UserEntitlement, free_limit: int = 7) -> UserEntitlement:
    # Only call after a catalogue question is actually delivered successfully.
    if not has_active_subscription(entitlement) and entitlement.free_questions_used < free_limit:
        entitlement.free_questions_used += 1
    return entitlement
