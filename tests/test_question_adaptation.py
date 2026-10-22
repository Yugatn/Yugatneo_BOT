from app.services.question_adaptation import DialoguePreferences, topic_allowed, adapt_question
from app.telegram_polling import available_question_categories


def test_health_topics_are_opt_in():
    base = DialoguePreferences()
    assert not topic_allowed("chronic-health", base)
    assert topic_allowed("chronic-health", DialoguePreferences(chronic_health_topic=True))
    assert "Жизнь с хроническим состоянием" not in available_question_categories()
    assert "Жизнь с хроническим состоянием" in available_question_categories(
        DialoguePreferences(chronic_health_topic=True)
    )


def test_youth_and_age_relevant_topics():
    assert topic_allowed("adolescents", DialoguePreferences(age_group="under_18"))
    assert not topic_allowed("adolescents", DialoguePreferences(age_group="adult"))
    assert topic_allowed("older-adults", DialoguePreferences(age_group="older_adult"))
    assert not topic_allowed("psychodynamic", DialoguePreferences(age_group="under_18", sensitive_opt_in=True))


def test_gender_has_no_stereotyped_effect_on_selection():
    a = DialoguePreferences(gender_self_description="женщина")
    b = DialoguePreferences(gender_self_description="мужчина")
    assert topic_allowed("coaching", a) == topic_allowed("coaching", b)


def test_short_accessible_format_and_invalid_preferences():
    assert adapt_question("Что важно?", DialoguePreferences(format="short", accessible=True)).startswith("Можно ответить коротко.")
    import pytest
    with pytest.raises(ValueError):
        DialoguePreferences(age_group="invalid")
