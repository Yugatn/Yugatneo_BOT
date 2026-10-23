"""Small, deterministic offline beta-readiness checklist.

This is a development planning aid, not authorization to deploy.
"""
from __future__ import annotations

from app.services.quality_report import quality_report


REQUIRED_EXTERNAL_REVIEWS = (
    "clinical_content_review",
    "privacy_and_data_protection_review",
    "security_penetration_test",
    "load_and_recovery_drill",
    "incident_response_drill",
)


def beta_readiness() -> dict[str, object]:
    offline = quality_report()
    return {
        "offline_scenarios": offline["total"],
        "offline_passed": offline["passed"],
        "offline_gate_passed": offline["ready_for_controlled_review"],
        "external_reviews_pending": list(REQUIRED_EXTERNAL_REVIEWS),
        "approved_for_public_release": False,
        "approved_for_closed_beta": False,
        "decision": "human_review_required",
    }
