from app.telegram_polling import branch_catalog_suggestion, terminal_keyboard
from app.services.question_adaptation import DialoguePreferences
from app.services.branching_dialogue import question_context


def test_terminal_keyboard_explicit_consent():
    labels = [item["text"] for row in terminal_keyboard()["keyboard"] for item in row]
    assert "🤖 Продолжить с ИИ" in labels
    assert "↩️ Главное меню" in labels


def test_branch_catalog_suggestion_uses_safe_catalog():
    result = branch_catalog_suggestion("anxiety", DialoguePreferences())
    assert result.startswith("\\n\\nВопрос из библиотеки")


def test_handoff_context_is_not_diagnostic():
    text = question_context("anxiety")
    assert "Не делай диагностических выводов" in text
