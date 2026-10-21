from app.services.catalog import load_questions


def test_catalog_has_questions_and_stable_ids():
    questions = load_questions()
    assert len(questions) >= 100
    ids = [question.id for question in questions]
    assert len(ids) == len(set(ids))
    assert all(question.text.strip() for question in questions)
