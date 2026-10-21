"""Optional, transparent project support. Core bot access must never depend on payment."""
from app.core.config import get_settings


def support_buttons() -> list[dict[str, str]]:
    settings = get_settings()
    if not settings.tribute_enabled:
        return []
    buttons: list[dict[str, str]] = []
    if settings.tribute_support_url:
        buttons.append({
            "label": "Добровольно поддержать через Tribute",
            "value": "support:tribute",
            "url": settings.tribute_support_url,
        })
    if settings.tribute_paid_product_url:
        buttons.append({
            "label": "Другие варианты поддержки",
            "value": "support:tribute_product",
            "url": settings.tribute_paid_product_url,
        })
    return buttons


def support_notice() -> str:
    settings = get_settings()
    if not settings.tribute_enabled or not (settings.tribute_support_url or settings.tribute_paid_product_url):
        return ""
    return (
        "\n\nДоступ к Yugatneo BOT бесплатный. Если проект оказался полезен, "
        "ты можешь по желанию поддержать его через Tribute. Оплата не открывает "
        "и не закрывает базовые вопросы, диалог или функции безопасности."
    )
