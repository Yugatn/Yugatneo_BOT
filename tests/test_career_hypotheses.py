import pytest

from app.services.career_questionnaires import begin_questionnaire
from app.services.guided_reflection import advance
from app.services.career_hypotheses import career_hypotheses


def complete(values):
    session = begin_questionnaire("career")
    for value in values:
        session = advance(session, value)
    return session


def test_hypotheses_are_grounded_and_not_predictions():
    session = complete(["Разработка игр и монтаж видео", "Создавал игры", "Python",
                        None, None, None])
    result = career_hypotheses(session)
    assert "Создание цифровых продуктов" in result
    assert "Визуальное творчество" in result
    assert "не прогноз успеха" in result


def test_unknown_interests_dont_invent_career():
    session = complete([None] * 6)
    result = career_hypotheses(session, "en")
    assert "Not enough specific interests" in result
    assert "not predictions" in result


def test_constraints_cannot_be_misinterpreted_as_interests():
    session = complete([None, None, None, None, "I cannot afford game development", None])
    result = career_hypotheses(session, "en")
    assert "Not enough specific interests" in result


def test_wrong_questionnaire_or_incomplete_rejected():
    with pytest.raises(ValueError):
        career_hypotheses(begin_questionnaire("career"))
    with pytest.raises(ValueError):
        career_hypotheses(complete([None] * 6), "de")
