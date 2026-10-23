"""Regression tests for the compact parenting knowledge index."""
from app.services.parenting_index import init_index, search_index


def test_parenting_index_round_trip(tmp_path):
    db = tmp_path / "parenting.sqlite3"
    init_index(db)
    matches = search_index(db, "conflict")
    assert len(matches) == 1
    assert matches[0].key == "conflict"
    assert "конфликт" in matches[0].tags
    init_index(db)
    assert len(search_index(db, "conflict")) == 1


def test_parenting_index_russian_tags(tmp_path):
    db = tmp_path / "parenting.sqlite3"
    init_index(db)
    assert any(topic.key == "toddler" for topic in search_index(db, "границы"))
    assert search_index(db, "несуществующая-тема") == ()


def test_parenting_index_no_unbounded_results(tmp_path):
    db = tmp_path / "parenting.sqlite3"
    init_index(db)
    assert len(search_index(db, "а", limit=2)) <= 2
