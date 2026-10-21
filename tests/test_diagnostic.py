from app.services.catalog import load_questions
from app.services.diagnostic import DiagnosticProfile, prioritize_questions


def test_diagnostic_prioritizes_stabilization_when_distress_is_high():
    result = prioritize_questions(
        load_questions(),
        DiagnosticProfile(age=34, goal="conditioning", distress=4, urgency="high"),
        limit=12,
    )
    assert result["first_categories"][0] == "resources"
    assert result["mode"] == "non_clinical_question_prioritization"
    assert result["questions"]
    assert "не диагноз" in result["notice"]


def test_diagnostic_respects_goal_and_self_reported_style():
    result = prioritize_questions(
        load_questions(),
        DiagnosticProfile(
            age=28,
            gender="не указывать",
            temperament="phlegmatic",
            psychotype="аналитический (самоописание)",
            goal="relationships",
            distress=1,
            urgency="normal",
            style="gentle",
        ),
        limit=10,
    )
    assert "relationships" in result["first_categories"]
    assert result["profile_used"]["temperament_self_report"] == "phlegmatic"
    assert result["profile_used"]["gender_self_description_provided"] is True


def test_diagnostic_rejects_invalid_scales():
    try:
        prioritize_questions(load_questions(), DiagnosticProfile(age=30, distress=5))
    except ValueError as exc:
        assert "distress" in str(exc)
    else:
        raise AssertionError("Expected invalid distress score to be rejected")


def test_diagnostic_catalog_questions_have_unique_ids():
    result = prioritize_questions(load_questions(), DiagnosticProfile(age=17), limit=15)
    ids = [item["id"] for item in result["questions"]]
    assert len(ids) == len(set(ids))
