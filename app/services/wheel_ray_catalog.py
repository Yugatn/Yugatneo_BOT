"""Configurable non-diagnostic balance-wheel rays.

The nine core domains are defaults, not mandatory categories. Users may add,
rename or omit rays. Scores represent self-report, never a clinical metric.
"""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Ray:
    key: str
    title: str
    facets: tuple[str, ...]


RAYS = (
    Ray("health", "Здоровье", ("сон", "питание", "движение", "восстановление", "самочувствие", "доступ к медицинской помощи")),
    Ray("work", "Работа", ("интерес к деятельности", "условия труда", "нагрузка", "автономия", "профессиональная устойчивость")),
    Ray("finance", "Финансы", ("доход", "расходы", "подушка безопасности", "долги", "финансовые цели")),
    Ray("relationships", "Отношения", ("близость", "границы", "взаимность", "общение", "разрешение конфликтов")),
    Ray("social", "Социальная жизнь", ("дружба", "сообщество", "поддержка", "участие", "принадлежность")),
    Ray("rest", "Отдых", ("досуг", "восстановление", "баланс нагрузки", "впечатления", "свободное время")),
    Ray("development", "Развитие", ("обучение", "навыки", "любознательность", "практика", "самостоятельность")),
    Ray("creativity", "Творчество", ("самовыражение", "идеи", "практика", "завершение работ", "удовольствие от процесса")),
    Ray("self", "Самоощущение", ("ценности", "эмоциональное состояние", "самопринятие", "смысл", "личные границы")),
)

# Additional opt-in domains, not assumed to apply to everyone.
OPTIONAL_RAYS = (
    Ray("home", "Дом и быт", ("жильё", "комфорт", "безопасность", "порядок")),
    Ray("family", "Семья", ("общение", "поддержка", "границы", "совместное время")),
    Ray("parenting", "Родительство", ("контакт", "поддержка", "ресурсы", "границы")),
    Ray("environment", "Среда", ("экология", "доступность", "транспорт", "общественные пространства")),
    Ray("citizenship", "Общество и гражданская жизнь", ("участие", "права", "солидарность", "взаимопомощь")),
    Ray("digital", "Цифровая среда", ("безопасность", "приватность", "цифровая нагрузка", "автономия")),
    Ray("spiritual", "Мировоззрение", ("ценности", "убеждения", "вопросы смысла", "свобода выбора")),
    Ray("intimacy", "Интимность", ("личные границы", "взаимное согласие", "комфорт", "общение")),
    Ray("fears", "Страхи и устойчивость", ("осознание страхов", "стратегии совладания", "поддержка", "обращение за помощью")),
    Ray("habits", "Привычки", ("саморегуляция", "режим", "гибкость", "изменение поведения")),
)


def normalize_ray_title(value: str) -> str:
    """Validate a user-chosen ray name without guessing its meaning."""
    title = re.sub(r"\s+", " ", value).strip()
    if not 1 <= len(title) <= 80:
        raise ValueError("Название луча должно содержать от 1 до 80 символов")
    if any(ord(ch) < 32 for ch in title):
        raise ValueError("Недопустимые управляющие символы")
    return title


def catalog(include_optional: bool = False) -> tuple[Ray, ...]:
    return RAYS + OPTIONAL_RAYS if include_optional else RAYS


def describe_ray(key: str) -> Ray | None:
    return next((ray for ray in catalog(True) if ray.key == key), None)
