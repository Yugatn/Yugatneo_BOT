"""Six-section menu retains access to all existing feature handlers."""
from app.telegram_polling import MENU, SUBMENUS, submenu_keyboard


def test_home_has_six_entries():
    buttons = [button["text"] for row in MENU["keyboard"] for button in row]
    assert len(buttons) == 6
    assert len(set(buttons)) == 6


def test_submenus_offer_back_navigation():
    for name in SUBMENUS:
        keyboard = submenu_keyboard(name)
        assert keyboard["keyboard"][-1][0]["text"] == "↩️ Главное меню"


def test_all_legacy_actions_remain_reachable():
    available = {button["text"] for row in MENU["keyboard"] for button in row}
    for rows in SUBMENUS.values():
        available.update(label for row in rows for label in row)
    for action in (
        "💬 Рефлексия", "🧠 Выбрать подход", "📚 Вопросы",
        "🎓 Навыки и профессии", "👨‍👩‍👧 Родительство",
        "🌐 Язык / Language", "📄 Мой отчёт", "📈 История колеса",
        "🗑 Удалить мои данные",
    ):
        assert action in available
