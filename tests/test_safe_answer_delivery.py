from app.services.safe_answer_delivery import (
    source_bounded_answer, review_external_draft,
)


def test_source_only_parenting_answer_is_delivered_with_citations():
    result = source_bounded_answer("parenting")
    assert result.delivered
    assert "https://" in result.text
    assert "Bandura" in result.text


def test_unknown_topic_fails_closed():
    result = source_bounded_answer("unverified_topic")
    assert not result.delivered
    assert result.findings == ("no_sources",)
    assert "Не удалось проверить" in result.text


def test_unreviewed_ai_draft_never_published_even_if_structurally_valid():
    draft = "Observation can influence learning."
    result = review_external_draft(
        draft, topic="parenting", locale="en", cited_ids=("learning_social",)
    )
    assert not result.delivered
    assert "human_review_required" in result.findings
    assert draft not in result.text


def test_unreviewed_ai_draft_with_diagnosis_stays_blocked():
    result = review_external_draft(
        "You have depression.", topic="parenting", locale="en",
        cited_ids=("learning_social",)
    )
    assert not result.delivered
    assert "unsupported_diagnosis" in result.findings


def test_age_gated_author_concepts_cannot_leak_via_default_delivery():
    result = source_bounded_answer("philosophy", age=17)
    assert not result.delivered
    assert "no_sources" in result.findings
