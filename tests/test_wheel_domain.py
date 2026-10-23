import pytest
from app.services.wheel_domain import RayScore, normalize_assessment, compare_assessments, new_snapshot


def test_comparison_ignores_missing_rays():
    assert compare_assessments([RayScore("health", 4), RayScore("work", 8)],
                               [RayScore("health", 6), RayScore("new", 9)]) == {"health": 2}


def test_zero_is_valid_and_missing_is_not_zero():
    assert compare_assessments([], [RayScore("health", 0)]) == {}


@pytest.mark.parametrize("score", [-1, 11, 2.5, True])
def test_invalid_scores(score):
    with pytest.raises(ValueError):
        RayScore("health", score)


def test_duplicate_rays_rejected():
    with pytest.raises(ValueError):
        normalize_assessment([RayScore("health", 2), RayScore("health", 3)])


def test_snapshot_retains_version_and_order():
    snapshot = new_snapshot([RayScore("work", 7), RayScore("health", 3)], 2)
    assert snapshot["wheel_version"] == 2
    assert [a["ray_id"] for a in snapshot["answers"]] == ["work", "health"]
