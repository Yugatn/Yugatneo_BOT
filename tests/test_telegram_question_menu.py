"""Regression checks for offline Russian question selection."""
from app.telegram_polling import (
    CATALOG,
    MENU,
    SUBMENUS,
    available_question_categories,
    question_keyboard,
)


def test_main_menu_has_question_library():
    labels = [button["text"] for row in MENU["keyboard"] for button in row]
    assert "💬 Коучинг" in labels
    assert "📚 Вопросы" in [item for row in SUBMENUS["💬 Коучинг"] for item in row]


def test_topics_are_russian_and_only_have_standard_questions():
    topics = available_question_categories()
    assert topics
    assert len(topics) == len(set(topics))
    for label, category in topics.items():
        assert any("а" <= letter.lower() <= "я" or letter.lower() == "ё" for letter in label)
        assert any(
            question.category == category and question.risk_level == "standard"
            for question in CATALOG.questions
        )
    assert "change-and-loss" not in topics.values()


def test_keyboard_lists_all_safe_topics_and_exit():
    keyboard = question_keyboard()
    labels = [button["text"] for row in keyboard["keyboard"] for button in row]
    assert set(available_question_categories()).issubset(labels)
    assert "↩️ Главное меню" in labels
