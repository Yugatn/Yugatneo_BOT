from app.services.coaching_session import Session, Stage, advance, erase


def test_consent_is_explicit():
    session = Session()
    for answer in ("", "может быть"):
        session, _ = advance(session, answer)
        assert session.stage == Stage.CONSENT
    session, _ = advance(session, "да")
    assert session.stage == Stage.GOAL


def test_full_session():
    session, _ = advance(Session(), "да")
    for answer in ("цель", "факты", "два варианта", "малый шаг", "завтра"):
        session, _ = advance(session, answer)
    assert session.stage == Stage.DONE
    assert len(session.answers) == 5


def test_cancel_drops_answers():
    session, _ = advance(Session(), "да")
    session, _ = advance(session, "личный ответ")
    session, _ = advance(session, "/cancel")
    assert session.stage == Stage.CANCELLED
    assert session.answers == ()


def test_empty_or_oversized_answer_rejected():
    session, _ = advance(Session(), "да")
    for answer in ("", "x" * 2001):
        result, _ = advance(session, answer)
        assert result == session


def test_erase():
    assert erase(Session(Stage.ACTION, (("goal", "secret"),))).answers == ()
