from app.core.models import UserEntitlement
from app.services.access import can_access_question, record_question_use


def test_first_seven_questions_are_free():
    entitlement = UserEntitlement(user_id="u1")
    for expected_remaining in range(7, 0, -1):
        decision = can_access_question(entitlement, free_limit=7)
        assert decision.allowed is True
        assert decision.remaining_free == expected_remaining
        record_question_use(entitlement, free_limit=7)
    decision = can_access_question(entitlement, free_limit=7)
    assert decision.allowed is False
    assert decision.reason == "subscription_required"


def test_active_subscription_unlocks_catalog():
    entitlement = UserEntitlement(user_id="u2", free_questions_used=7, subscription_active=True)
    assert can_access_question(entitlement, free_limit=7).allowed is True
