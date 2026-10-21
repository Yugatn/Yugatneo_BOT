"""Access policy: the core question catalogue is free without a usage cap.

Tribute is an optional support channel and never changes access to core features.
"""
from app.core.models import UserEntitlement


class AccessDecision:
    def __init__(self, allowed: bool, reason: str, remaining_free: int = 0):
        self.allowed = allowed
        self.reason = reason
        self.remaining_free = remaining_free


def has_active_subscription(entitlement: UserEntitlement) -> bool:
    """Kept for compatibility with future optional paid add-ons; not required for core access."""
    return False


def can_access_question(entitlement: UserEntitlement, free_limit: int = 7) -> AccessDecision:
    return AccessDecision(True, "unlimited_free_access", -1)


def record_question_use(entitlement: UserEntitlement, free_limit: int = 7) -> UserEntitlement:
    """Track use for analytics if desired; never stop access after the former free limit."""
    entitlement.free_questions_used += 1
    return entitlement
