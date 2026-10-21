from types import SimpleNamespace

from app.services import diagnostic_flow
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


def test_interactive_flow_completes_and_adapts_goal(tmp_path, monkeypatch):
    db = tmp_path / "diagnostic.sqlite3"
    monkeypatch.setattr(diagnostic_flow, "get_settings", lambda: SimpleNamespace(database_url=f"sqlite:///{db}"))
    channel, user = "telegram", "test-user"

    started = diagnostic_flow.start_diagnostic(channel, user)
    assert started["metadata"]["diagnostic"] == "started"

    steps = [
        "34",
        "diagnostic:goal:conditioning",
        "diagnostic:distress:2",
        "diagnostic:style:structured",
        "diagnostic:temperament:unsure",
        "пропустить",
        "аналитический",
    ]
    result = None
    for answer in steps:
        result = diagnostic_flow.handle_diagnostic_message(channel, user, answer)

    assert result is not None
    assert result["metadata"]["diagnostic"] == "completed"
    assert result["metadata"]["first_question_id"]

    context = diagnostic_flow.adaptive_context(channel, user, "У меня конфликт с партнёром")
    assert "relationships" in context
    recommendation = diagnostic_flow.recommendation_for(channel, user)
    assert recommendation is not None


def test_diagnostic_can_be_skipped_and_reconfigured(tmp_path, monkeypatch):
    db = tmp_path / "diagnostic.sqlite3"
    monkeypatch.setattr(diagnostic_flow, "get_settings", lambda: SimpleNamespace(database_url=f"sqlite:///{db}"))
    channel, user = "telegram", "another-user"
    diagnostic_flow.start_diagnostic(channel, user)
    skipped = diagnostic_flow.handle_diagnostic_message(channel, user, "пропустить диагностику")
    assert skipped["metadata"]["diagnostic"] == "skipped"

    diagnostic_flow.start_diagnostic(channel, user)
    first_answer = diagnostic_flow.handle_diagnostic_message(channel, user, "29")
    assert first_answer["metadata"]["step"] == "goal"
    restarted = diagnostic_flow.handle_diagnostic_message(channel, user, "сменить тему")
    assert restarted["metadata"]["diagnostic"] == "started"
