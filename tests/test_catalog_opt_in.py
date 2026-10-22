import json
from app.services.question_catalog import QuestionCatalog


def test_opt_in_never_unlocks_sensitive_or_restricted(tmp_path):
    questions = [
        {'id': name, 'category': 'review', 'text': 'Что сейчас важно?',
         'tags': [], 'risk_level': name}
        for name in ('sensitive', 'restricted', 'high', 'reflective')
    ]
    path = tmp_path / 'catalog.json'
    path.write_text(json.dumps({'count': len(questions), 'questions': questions}), encoding='utf-8')
    catalog = QuestionCatalog(path)
    assert catalog.select('review') is None
    assert catalog.select('review', allow_sensitive=True).id == 'reflective'
