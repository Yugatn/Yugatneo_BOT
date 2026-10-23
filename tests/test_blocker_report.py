from app.services.blocker_report import blocker_report


def test_blockers_are_explicit_and_release_is_blocked():
    report = blocker_report()
    assert report["deployment_allowed"] is False
    assert report["status"] == "blocked_pending_review"
    assert report["offline_scenarios"] >= 14
    assert len(report["blocking_reviews"]) >= 4
    assert all(item["status"] == "not_verified" for item in report["blocking_reviews"])
