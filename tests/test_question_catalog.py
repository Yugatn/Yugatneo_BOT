import json
from pathlib import Path

import pytest

from app.services.question_catalog import QuestionCatalog


def test_builtin_catalog_is_valid():
    catalog = QuestionCatalog()
    assert len(catalog.questions) == 430
    assert len(catalog.categories()) == 43
    assert len({q.id for q in catalog.questions}) == len(catalog.questions)


def test_sensitive_items_are_not_auto_selected():
    catalog = QuestionCatalog()
    for category in catalog.categories():
        q = catalog.select(category)
        if q is not None:
            assert q.risk_level == "standard"
            assert q.category == category
            assert catalog.select(category, seen_ids={q.id}) != q


def test_duplicate_id_rejected(tmp_path: Path):
    path = tmp_path / "catalog.json"
    row = {
        "id": "duplicate", "category": "coaching", "text": "Какова цель?",
        "risk_level": "standard", "tags": []
    }
    path.write_text(json.dumps({"count": 2, "questions": [row, row]}), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        QuestionCatalog(path)


def test_declared_count_rejected(tmp_path: Path):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"count": 4, "questions": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="count"):
        QuestionCatalog(path)
