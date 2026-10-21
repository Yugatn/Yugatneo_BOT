from app.services.catalog import load_questions


def test_catalog_has_expanded_question_bank_and_stable_ids():
    questions = load_questions()
    assert len(questions) >= 300
    ids = [question.id for question in questions]
    assert len(ids) == len(set(ids))
    assert all(question.text.strip() for question in questions)


def test_catalog_includes_deconditioning_topics():
    categories = {question.category for question in load_questions()}
    assert "conditioning-norms" in categories
    assert "identity-narratives" in categories
    assert "autonomy" in categories
    assert "integration" in categories
