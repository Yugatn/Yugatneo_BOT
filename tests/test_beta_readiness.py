from app.services.beta_readiness import beta_readiness, REQUIRED_EXTERNAL_REVIEWS


def test_beta_readiness_never_auto_approves_deployment():
    result = beta_readiness()
    assert result["offline_scenarios"] >= 14
    assert result["offline_passed"] <= result["offline_scenarios"]
    assert result["approved_for_closed_beta"] is False
    assert result["approved_for_public_release"] is False
    assert result["decision"] == "human_review_required"
    assert set(result["external_reviews_pending"]) == set(REQUIRED_EXTERNAL_REVIEWS)
