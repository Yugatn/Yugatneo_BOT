import json
from app.services.question_catalog import QuestionCatalog


def test_builtin_risk_totals():
    catalog = QuestionCatalog()
    assert catalog.by_risk['standard'] == 320
    assert catalog.by_risk['reflective'] == 100
    assert catalog.by_risk['sensitive'] == 10


def test_unclassified_question_rejected(tmp_path):
    path = tmp_path / 'questions.json'
    path.write_text(json.dumps({'count': 1, 'questions': [
        {'id': 'sample', 'category': 'test', 'text': 'Как дела?', 'tags': []}
    ]}), encoding='utf-8')
    try:
        QuestionCatalog(path)
    except ValueError as exc:
        assert 'risk level' in str(exc)
    else:
        raise AssertionError('Unclassified question accepted')
