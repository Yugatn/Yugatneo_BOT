"""Non-diagnostic adaptation of reflective questions.

Do not infer gender, disability, disease, or mental health condition.
Only explicitly volunteered needs influence presentation and topic eligibility.
"""
from dataclasses import dataclass

AGE_GROUPS = ("unknown", "under_18", "adult", "older_adult")
FORMATS = ("short", "standard")


@dataclass(frozen=True)
class DialoguePreferences:
    age_group: str = "unknown"
    format: str = "standard"
    accessible: bool = False
    chronic_health_topic: bool = False
    sensitive_opt_in: bool = False
    gender_self_description: str | None = None

    def __post_init__(self):
        if self.age_group not in AGE_GROUPS or self.format not in FORMATS:
            raise ValueError("Invalid dialogue preferences")


def topic_allowed(category: str, prefs: DialoguePreferences) -> bool:
    """Eligibility is conservative; identity is never used as a proxy for need."""
    if category == "chronic-health" and not prefs.chronic_health_topic:
        return False
    if category in {"psychodynamic", "identity"} and not prefs.sensitive_opt_in:
        return False
    if category == "adolescents" and prefs.age_group != "under_18":
        return False
    if category == "older-adults" and prefs.age_group != "older_adult":
        return False
    if prefs.age_group == "under_18" and category in {"psychodynamic", "identity"}:
        return False
    return True


def adapt_question(text: str, prefs: DialoguePreferences) -> str:
    """Avoid rewriting clinical meaning. Offer presentation accommodations only."""
    prefix = "Можно ответить коротко. " if prefs.format == "short" else ""
    suffix = " Можно пропустить вопрос." if prefs.accessible else ""
    return prefix + text + suffix


def voluntary_intro() -> str:
    return (
        "Можно уточнить возрастную группу и удобный формат вопросов. "
        "Сведения о здоровье и гендере не обязательны и не нужны для доступа к боту. "
        "Бот не определяет диагноз и не назначает лечение."
    )
