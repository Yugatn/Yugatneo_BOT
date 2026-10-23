from app.services.answer_quality import evaluate_answer


def test_source_backed_neutral_parenting_answer():
    result = evaluate_answer(
        "Наблюдение за поведением взрослых может влиять на обучение детей.",
        topic="parenting", cited_ids=("learning_social",)
    )
    assert result.approved


def test_unsupported_diagnosis_rejected():
    result = evaluate_answer(
        "У вас депрессия.", topic="parenting",
        cited_ids=("learning_social",)
    )
    assert not result.approved
    assert "unsupported_diagnosis" in result.findings


def test_hypothesis_as_science_rejected():
    result = evaluate_answer(
        "Научно доказано, что амбивалентный солипсизм объясняет мир.",
        topic="philosophy", age=18, include_author_hypotheses=True,
        cited_ids=("author_philosophy",)
    )
    assert "hypothesis_as_science" in result.findings


def test_unknown_or_age_blocked_citations_rejected():
    result = evaluate_answer(
        "Это философская концепция.", topic="philosophy", age=16,
        include_author_hypotheses=True, cited_ids=("author_philosophy",)
    )
    assert "unavailable_citation:author_philosophy" in result.findings


def test_missing_citation_and_duplicate_citations_rejected():
    missing = evaluate_answer("Текст", topic="parenting")
    assert "missing_citations" in missing.findings
    duplicated = evaluate_answer("Текст", topic="parenting",
                                 cited_ids=("scaffolding", "scaffolding"))
    assert "duplicate_citations" in duplicated.findings


def test_english_unsubstantiated_guarantee_rejected():
    result = evaluate_answer(
        "This is a guaranteed cure", topic="parenting",
        locale="en", cited_ids=("violence_prevention",)
    )
    assert "unsupported_treatment_guarantee" in result.findings
