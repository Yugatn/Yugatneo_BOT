import pytest

from app.services.knowledge_index import ENTRIES, lookup, KNOWLEDGE_VERSION


def test_index_has_unique_ids_and_sources():
    assert KNOWLEDGE_VERSION
    assert len({entry.id for entry in ENTRIES}) == len(ENTRIES)
    assert all(entry.source and entry.source_url.startswith("https://") for entry in ENTRIES)


def test_parenting_has_bilingual_sources_and_evidence_labels():
    ru = lookup("parenting", locale="ru")
    en = lookup("parenting", locale="en")
    assert len(ru) == len(en) >= 3
    assert {entry["id"] for entry in ru} == {entry["id"] for entry in en}
    assert all(entry["evidence"] in {"theory", "guideline", "research"} for entry in ru)


def test_author_philosophy_is_opt_in_and_age_restricted():
    assert lookup("philosophy") == []
    assert lookup("philosophy", age=17, include_author_hypotheses=True) == []
    assert lookup("philosophy", include_author_hypotheses=True) == []
    adult = lookup("philosophy", age=18, include_author_hypotheses=True)
    assert len(adult) == 1
    assert adult[0]["evidence"] == "author_hypothesis"


def test_unknown_locale_is_rejected():
    with pytest.raises(ValueError):
        lookup("parenting", locale="de")
