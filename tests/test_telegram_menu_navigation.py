"""Keep Telegram navigation unambiguous and free of duplicate buttons."""
from app.telegram_polling import SUBMENUS, submenu_keyboard


def test_submenu_buttons_are_unique():
    for section, rows in SUBMENUS.items():
        labels = [label for row in rows for label in row]
        assert len(labels) == len(set(labels)), section


def test_each_submenu_has_return_button():
    for section in SUBMENUS:
        keyboard = submenu_keyboard(section)
        assert keyboard["keyboard"][-1] == [{"text": "↩️ Главное меню"}]
