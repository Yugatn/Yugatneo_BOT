from app.services.interface_i18n import MESSAGES, tr


def test_core_translations_cover_both_languages():
    for key, translations in MESSAGES.items():
        assert translations["ru"].strip(), key
        assert translations["en"].strip(), key


def test_translation_substitution_and_fallback():
    assert "health" in tr("en", "wheel_score_prompt", sphere="health")
    assert "здоровье" in tr("ru", "wheel_score_prompt", sphere="здоровье")
    assert tr("unknown", "career_intro") == tr("ru", "career_intro")


def test_missing_translation_key_fails_closed():
    import pytest
    with pytest.raises(KeyError):
        tr("en", "not_a_real_key")
