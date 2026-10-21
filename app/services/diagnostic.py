"""Lightweight, non-clinical question prioritization based on self-reported preferences."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


TEMPERAMENTS = {"sanguine", "choleric", "phlegmatic", "melancholic", "unsure"}
STYLES = {"structured", "open", "direct", "gentle", "unsure"}
GOAL_CATEGORIES = {
    "emotions": ["emotions", "stress", "wellbeing", "resources"],
    "anxiety": ["anxiety", "uncertainty-control", "stress", "wellbeing"],
    "relationships": ["relationships", "boundaries", "conflict", "self-compassion"],
    "goals": ["goals", "values", "decisions", "habits"],
    "identity": ["situation", "values", "identity-narratives", "autonomy"],
    "conditioning": ["situation", "conditioning-norms", "automatic-patterns", "autonomy"],
    "work": ["work", "goals", "decisions", "wellbeing"],
    "general": ["situation", "resources", "emotions", "values"],
}


@dataclass(frozen=True)
class DiagnosticProfile:
    age: int
    gender: str | None = None
    temperament: str = "unsure"
    psychotype: str = "unsure"
    goal: str = "general"
    distress: int = 1
    urgency: str = "normal"
    style: str = "unsure"


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def prioritize_questions(questions: list[Any], profile: DiagnosticProfile, limit: int = 12) -> dict[str, Any]:
    """Return a personalized sequence. This is routing, not diagnosis or personality inference."""
    if not 1 <= profile.age <= 120:
        raise ValueError("age must be between 1 and 120")
    if not 0 <= profile.distress <= 4:
        raise ValueError("distress must be between 0 and 4")
    if profile.temperament not in TEMPERAMENTS:
        raise ValueError("unsupported temperament")
    if profile.style not in STYLES:
        raise ValueError("unsupported style")
    if profile.urgency not in {"normal", "soon", "high"}:
        raise ValueError("unsupported urgency")

    goal = profile.goal if profile.goal in GOAL_CATEGORIES else "general"
    preferred = list(GOAL_CATEGORIES[goal])
    # Start with orientation and stabilization; do not interpret urgency as a diagnosis.
    if profile.distress >= 3 or profile.urgency == "high":
        preferred = _unique(["resources", "wellbeing", "stress", "emotions", "situation"] + preferred)
    elif profile.distress == 2:
        preferred = _unique(["situation", "emotions", "resources", "stress"] + preferred)
    else:
        preferred = _unique(["situation"] + preferred)

    # Preferences alter the conversation pace, not assumptions about the person's abilities.
    temperament_additions = {
        "sanguine": ["creativity", "relationships", "goals"],
        "choleric": ["decisions", "goals", "boundaries"],
        "phlegmatic": ["wellbeing", "values", "self-compassion"],
        "melancholic": ["beliefs", "self-compassion", "cognitive-biases"],
        "unsure": [],
    }
    style_additions = {
        "structured": ["situation", "decisions", "integration"],
        "open": ["values", "identity-narratives", "autonomy"],
        "direct": ["goals", "decisions", "habits"],
        "gentle": ["self-compassion", "resources", "wellbeing"],
        "unsure": [],
    }
    preferred = _unique(preferred + temperament_additions[profile.temperament] + style_additions[profile.style])

    # For minors, keep the default sequence concrete and supportive; never use age to infer maturity.
    if profile.age < 18:
        preferred = _unique(["situation", "wellbeing", "emotions", "resources", "stress"] + preferred)
        preferred = [c for c in preferred if c not in {"trauma-informed", "family-scripts"}]

    # Gender is only a self-description / language preference; it never changes psychological ranking.
    # "Psychotype" is self-reported and used only as optional context, not inferred or scored.
    by_category: dict[str, list[Any]] = {}
    for question in questions:
        category = getattr(question, "category", None) if not isinstance(question, dict) else question.get("category")
        if category:
            by_category.setdefault(category, []).append(question)

    ordered_categories = [c for c in preferred if c in by_category]
    remaining = sorted(c for c in by_category if c not in ordered_categories)
    ordered_categories.extend(remaining)

    ordered = []
    for category in ordered_categories:
        for question in by_category[category]:
            ordered.append(question)
    if not ordered:
        raise ValueError("question catalog is empty")

    def serialize(q: Any) -> dict[str, Any]:
        if isinstance(q, dict):
            return {key: q.get(key) for key in ("id", "category", "subcategory", "text", "purpose")}
        return {key: getattr(q, key) for key in ("id", "category", "subcategory", "text", "purpose")}

    selected = [serialize(q) for q in ordered[:max(1, min(limit, 30))]]
    last_categories = list(reversed(ordered_categories[-4:]))
    return {
        "mode": "non_clinical_question_prioritization",
        "notice": (
            "Это ориентировочная настройка порядка вопросов, а не психологический тест, "
            "диагноз или научно подтверждённое определение психотипа. Ответы не доказывают "
            "черты личности. Можно пропустить любой вопрос или изменить настройки."
        ),
        "profile_used": {
            "age_band": "under_18" if profile.age < 18 else "18_29" if profile.age < 30 else "30_44" if profile.age < 45 else "45_59" if profile.age < 60 else "60_plus",
            "gender_self_description_provided": bool((profile.gender or "").strip()),
            "temperament_self_report": profile.temperament,
            "psychotype_self_report": profile.psychotype or "unsure",
            "goal": goal,
            "distress_self_report": profile.distress,
            "urgency_self_report": profile.urgency,
            "preferred_style": profile.style,
        },
        "first_categories": ordered_categories[:5],
        "last_categories": last_categories,
        "questions": selected,
        "safety_note": (
            "Если есть непосредственная опасность, риск причинить вред себе или другому, "
            "либо состояние быстро ухудшается, приоритет — местная экстренная помощь и живой "
            "специалист, а не прохождение вопросов."
        ),
    }
