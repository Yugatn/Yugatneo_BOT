"""Transparent, user-led career exploration hypotheses.

Rules are illustrative interest matches, NOT predictive career aptitude scores.
No demographic, clinical or protected traits are inferred.
"""
from __future__ import annotations

import re

from app.services.guided_reflection import Session

RULES = (
    ("digital_creation", ("игр", "game", "roblox", "unity", "программ", "coding", "python"),
     "Создание цифровых продуктов и игр", "Digital products and game creation",
     "Создать небольшой прототип и оценить, понравился ли процесс.",
     "Build a small prototype and reflect on the experience."),
    ("visual_media", ("видео", "монтаж", "video", "editing", "рисован", "drawing", "design", "дизайн"),
     "Визуальное творчество и медиапроизводство", "Visual creativity and media production",
     "Сделать короткий ролик, рисунок или макет и собрать обратную связь.",
     "Create a short video, drawing or mockup and request feedback."),
    ("people", ("помог", "обуч", "teach", "help", "общен", "communication", "психолог"),
     "Обучение, коммуникация и помощь людям", "Education, communication and helping others",
     "Подготовить простое объяснение темы для добровольного слушателя.",
     "Explain a topic to a willing listener and ask what was clear."),
    ("craft", ("ремонт", "мастер", "craft", "repair", "wood", "дерев", "сборк"),
     "Ремесло, конструирование и практические задачи", "Crafts, making and practical work",
     "Выполнить небольшой безопасный проект с подходящими инструментами.",
     "Try a small, safe project with suitable tools."),
)


def career_hypotheses(session: Session, locale: str = "ru") -> str:
    if not session.finished:
        raise ValueError("Complete the questionnaire first")
    if locale not in {"ru", "en"}:
        raise ValueError("Unsupported language")
    if not session.questions or session.questions[0].id != "interests":
        raise ValueError("Career exploration session required")
    ru = locale == "ru"
    # Use stated interests and activities only, not obstacles or constraints.
    answers = {r.question_id: r.value or "" for r in session.responses}
    evidence = " ".join(answers.get(k, "") for k in ("interests", "experience", "skills"))
    tokens = re.findall(r"[\w]+", evidence.casefold())
    matches = []
    for _id, keywords, title_ru, title_en, step_ru, step_en in RULES:
        if any(any(token.startswith(keyword) for token in tokens) for keyword in keywords):
            matches.append((title_ru if ru else title_en, step_ru if ru else step_en))
    heading = ("Гипотезы для исследования (не оценка способностей)"
               if ru else "Ideas to explore (not an aptitude assessment)")
    lines = [heading]
    if matches:
        for title, experiment in matches[:3]:
            lines.append(f"• {title}\n  " +
                         ("Пробный шаг: " if ru else "Try: ") + experiment)
    else:
        lines.append(
            "Недостаточно конкретных интересов для примеров. Можно исследовать несколько направлений без выбора профессии сейчас."
            if ru else
            "Not enough specific interests for examples. You can explore several fields without choosing a career now."
        )
    lines.append(
        "Это примеры на основе указанных интересов, не прогноз успеха. "
        "Ты можешь отклонить любой вариант."
        if ru else
        "These are examples based on stated interests, not predictions of success. "
        "You can reject any suggestion."
    )
    return "\n\n".join(lines)
