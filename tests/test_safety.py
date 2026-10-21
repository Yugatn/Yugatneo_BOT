from app.services.safety import classify_crisis_message, crisis_response


def test_immediate_self_harm_message_gets_emergency_handoff():
    level = classify_crisis_message("Я собираюсь убить себя сегодня")
    assert level == "immediate"
    response = crisis_response(level)
    assert "экстренную службу" in response
    assert "непосредственной опасности" in response


def test_general_suicidal_ideation_gets_direct_safety_question():
    level = classify_crisis_message("Иногда я думаю о самоубийстве")
    assert level == "concern"
    assert "конкретный план" in crisis_response(level)


def test_ordinary_distress_is_not_classified_as_crisis():
    assert classify_crisis_message("Мне тревожно из-за собеседования") is None


def test_fictional_or_explicitly_negated_context_is_not_auto_classified():
    assert classify_crisis_message("Персонаж в романе думает о самоубийстве") is None
    assert classify_crisis_message("Я не хочу причинять себе вред") is None


def test_english_immediate_phrases_are_recognized():
    assert classify_crisis_message("I am going to kill myself today") == "immediate"



def test_immediate_intent_is_not_suppressed_by_fiction_context():
    assert classify_crisis_message("В романе персонаж говорит: я собираюсь убить себя сегодня") == "immediate"
