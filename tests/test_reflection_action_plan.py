import pytest

from app.services.guided_reflection import start, advance
from app.services.reflection_action_plan import build_action_plan


def finished(answers):
    session = start()
    for answer in answers:
        session = advance(session, answer)
    return session


def test_plan_only_uses_user_answers():
    plan = build_action_plan(finished(
        ["Make videos", "I edit clips", "Time", "A colleague", "Edit one minute"]
    ))
    for value in ("Make videos", "I edit clips", "Time", "A colleague", "Edit one minute"):
        assert value in plan
    assert "диагноз" not in plan
    assert "депрессия" not in plan


def test_skipped_step_does_not_invent_action():
    plan = build_action_plan(finished(["Study", None, None, None, None]))
    assert "Следующий шаг не выбран" in plan
    assert "Study" in plan


def test_english_plan():
    plan = build_action_plan(finished(["Learn design", None, None, None, "Draw daily"]), "en")
    assert "Your next-step plan" in plan
    assert "Draw daily" in plan


def test_incomplete_and_unknown_locale_rejected():
    with pytest.raises(ValueError):
        build_action_plan(start())
    with pytest.raises(ValueError):
        build_action_plan(finished([None] * 5), "xx")
