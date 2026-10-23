"""Conservative human-review blockers for beta planning."""
from __future__ import annotations

from app.services.beta_readiness import beta_readiness


def blocker_report() -> dict[str, object]:
    readiness = beta_readiness()
    return {
        "status": "blocked_pending_review",
        "offline_gate_passed": readiness["offline_gate_passed"],
        "offline_scenarios": readiness["offline_scenarios"],
        "offline_passed": readiness["offline_passed"],
        "blocking_reviews": [
            {"id": item, "status": "not_verified"}
            for item in readiness["external_reviews_pending"]
        ],
        "deployment_allowed": False,
        "note": "Offline tests are necessary but not sufficient for deployment.",
    }
