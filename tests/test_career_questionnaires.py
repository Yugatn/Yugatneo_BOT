from app.services.career_questionnaires import (
    QUESTIONNAIRES, QUESTIONNAIRE_VERSION, begin_questionnaire,
)
from app.services.guided_reflection import advance, summary


def test_questionnaires_are_versioned_and_have_unique_ids():
    assert QUESTIONNAIRE_VERSION
    for name, questions in QUESTIONNAIRES.items():
        assert len(questions) >= 5
        assert len({q.id for q in questions}) == len(questions)
        assert all(q.ru and q.en and q.optional for q in questions)
        assert begin_questionnaire(name).current.id == questions[0].id


def test_career_report_repeats_only_user_inputs():
    session = begin_questionnaire("career")
    for answer in ("Games", "Small game", "Drawing", "Programming", None, "Make a demo"):
        session = advance(session, answer)
    report = summary(session, "en")
    assert "Make a demo" in report
    assert "Drawing" in report
    assert "Skipped" in report
    assert "diagnosis" in report
    assert "You are talented" not in report


def test_skills_evidence_can_be_skipped_without_invented_certification():
    session = begin_questionnaire("skills")
    for answer in ("Video editing", "DaVinci Resolve", None, None, "Audio cleanup"):
        session = advance(session, answer)
    report = summary(session)
    assert "DaVinci Resolve" in report
    assert "Пропущено" in report
    assert "сертифицирован" not in report
