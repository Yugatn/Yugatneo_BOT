"""Grounded, non-diagnostic action plan from completed guided reflection.

This module never invents goals, obstacles, deadlines or professional advice.
"""
from __future__ import annotations

from app.services.guided_reflection import Session


def build_action_plan(session: Session, locale: str = "ru") -> str:
    if not session.finished:
        raise ValueError("A completed reflection is required")
    if locale not in ("ru", "en"):
        raise ValueError("Unsupported locale")
    values = {response.question_id: response.value
              for response in session.responses}
    ru = locale == "ru"
    lines = ["План следующего шага" if ru else "Your next-step plan"]
    fields = (
        ("goal", "Твоя цель", "Your goal"),
        ("strength", "На что можно опереться", "What is already working"),
        ("obstacle", "Названное препятствие", "Obstacle you identified"),
        ("resource", "Возможная поддержка", "Possible support"),
        ("step", "Выбранный тобой шаг", "Your chosen next step"),
    )
    for key, label_ru, label_en in fields:
        value = values.get(key)
        if value:
            lines.append(f"{label_ru if ru else label_en}: {value}")
    if not values.get("step"):
        lines.append(
            "Следующий шаг не выбран. Если захочешь, сформулируй одно небольшое действие."
            if ru else
            "No next step selected. If you wish, choose one small action."
        )
    lines.append(
        "Когда вернуться к этому плану — решаешь ты. "
        "Это отражение твоих слов, а не оценка личности."
        if ru else
        "You decide when to revisit this plan. "
        "It reflects your words, not a personality assessment."
    )
    return "\n\n".join(lines)
