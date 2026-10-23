import pytest

from app.services.guided_reflection import (
    Question, advance, start, summary, MAX_ANSWER,
)


def test_complete_reflection_without_invented_interpretations():
    session = start()
    for answer in ("Learn Python", "I can draw", None, "A friend", "Try a tutorial"):
        session = advance(session, answer)
    assert session.finished
    assert session.current is None
    text = summary(session)
    assert "Learn Python" in text
    assert "Пропущено" in text
    assert "Try a tutorial" in text
    assert "диагноз" in text
    assert "депрессия" not in text


def test_english_summary_and_immutability():
    original = start()
    updated = advance(original, "My goal")
    assert original.current.id == "goal"
    assert updated.current.id == "strength"
    for _ in range(4):
        updated = advance(updated, None)
    assert "My goal" in summary(updated, "en")
    assert "not a psychological diagnosis" in summary(updated, "en")


def test_reject_oversize_and_invalid_scale():
    session = start((Question("score", "Оценка", "Score", kind="scale"),))
    with pytest.raises(ValueError):
        advance(session, "11")
    with pytest.raises(ValueError):
        advance(session, "not-a-number")
    with pytest.raises(ValueError):
        advance(session, "x" * (MAX_ANSWER + 1))
    assert advance(session, "7").finished


def test_skip_required_question_is_rejected():
    session = start((Question("required", "Вопрос", "Question", optional=False),))
    with pytest.raises(ValueError):
        advance(session, None)


def test_no_summary_of_incomplete_session():
    with pytest.raises(ValueError):
        summary(start())


def test_no_duplicate_question_ids():
    question = Question("same", "Вопрос", "Question")
    with pytest.raises(ValueError):
        start((question, question))
