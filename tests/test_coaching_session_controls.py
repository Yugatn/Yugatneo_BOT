"""Offline regression tests for opt-in coaching navigation controls."""

from app.services.coaching_session import Session, Stage, advance


def _accepted() -> Session:
    session, _ = advance(Session(), "да")
    return session


def test_commands_cannot_bypass_consent():
    session = Session()
    for command in ("/skip", "/progress", "/repeat"):
        updated, _ = advance(session, command)
        assert updated == session
        assert updated.answers == ()


def test_skip_advances_without_recording_personal_data():
    session = _accepted()
    session, message = advance(session, "/skip")
    assert session.stage is Stage.EVIDENCE
    assert session.answers == ()
    assert "пропущен" in message.lower()
    session, _ = advance(session, "наблюдаемые факты")
    assert session.stage is Stage.OPTIONS
    assert session.answers == (("evidence", "наблюдаемые факты"),)


def test_repeat_and_progress_do_not_advance_or_store_answers():
    session = _accepted()
    for command in ("/repeat", "/progress", "повтори вопрос"):
        updated, message = advance(session, command)
        assert updated == session
        assert updated.answers == ()
        assert "цель" in message.lower()
    _, message = advance(session, "/progress")
    assert "1 из 5" in message


def test_skipped_questions_do_not_claim_complete_plan():
    session = _accepted()
    for _ in range(5):
        session, message = advance(session, "/skip")
    assert session.stage is Stage.DONE
    assert session.answers == ()
    assert "полный план не сформирован" in message
    assert "План сформирован." not in message


def test_complete_session_still_forms_plan():
    session = _accepted()
    for answer in ("цель", "факт", "варианты", "шаг", "завтра"):
        session, message = advance(session, answer)
    assert session.stage is Stage.DONE
    assert len(session.answers) == 5
    assert "План сформирован" in message


def test_cancellation_after_skip_forgets_answers():
    session = _accepted()
    session, _ = advance(session, "личная цель")
    session, _ = advance(session, "/skip")
    session, _ = advance(session, "/cancel")
    assert session.stage is Stage.CANCELLED
    assert session.answers == ()


def test_skip_does_not_bypass_max_length_limit_for_free_text():
    session = _accepted()
    updated, _ = advance(session, "а" * 2001)
    assert updated == session
    updated, _ = advance(session, "/skip")
    assert updated.stage is Stage.EVIDENCE
