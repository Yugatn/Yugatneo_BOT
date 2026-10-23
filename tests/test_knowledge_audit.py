from app.services.knowledge_audit import audit_knowledge


def test_parenting_sources_pass_structural_audit():
    result = audit_knowledge("parenting")
    assert result.passed
    assert result.sources_checked >= 3
    assert result.issues == ()


def test_author_hypothesis_not_included_by_default():
    result = audit_knowledge("philosophy")
    assert result.passed
    assert result.sources_checked == 0


def test_adult_opt_in_hypothesis_is_auditable():
    result = audit_knowledge("philosophy", age=18, include_author_hypotheses=True)
    assert result.passed
    assert result.sources_checked == 1
