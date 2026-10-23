"""Short RU/EN strings for the core self-reflection routes.

All English texts must remain educational, voluntary and non-diagnostic.
"""
from __future__ import annotations

MESSAGES = {
    "wheel_intro": {
        "ru": "Начнём колесо баланса. Назови сферу жизни своими словами. После этого оцени её от 0 до 10. /cancel — выход.",
        "en": "Let's explore your life balance. Name an area of your life in your own words (for example health, creativity or relationships). Then rate it from 0 to 10. /cancel — exit.",
    },
    "wheel_score_prompt": {
        "ru": "Как ты оцениваешь сферу «{sphere}» сейчас от 0 до 10? Это только твоя субъективная оценка.",
        "en": "How would you rate '{sphere}' right now from 0 to 10? This is your own subjective rating.",
    },
    "wheel_invalid": {
        "ru": "Введи целое число от 0 до 10. Для выхода — /cancel.",
        "en": "Enter a whole number from 0 to 10. To exit, use /cancel.",
    },
    "wheel_saved": {
        "ru": "Сохранено: {sphere} — {score}/10. Назови следующую сферу или /cancel.",
        "en": "Saved: {sphere} — {score}/10. Name another area or use /cancel.",
    },
    "career_intro": {
        "ru": "Какая деятельность тебе интересна? Например, игры, рисование или монтаж видео. Можно пока не знать будущую профессию. /cancel — выход.",
        "en": "What activities interest you? For example game design, drawing or video editing. You don't have to know your future profession yet. /cancel — exit.",
    },
    "career_skill": {
        "ru": "Что у тебя уже получается или чему ты пробовал учиться? Даже небольшой опыт считается.",
        "en": "What can you already do, or what have you tried learning? Even small experiences count.",
    },
    "career_experiment": {
        "ru": "Какой небольшой практический эксперимент поможет проверить этот интерес?",
        "en": "What small practical experiment could help you explore this interest?",
    },
    "career_saved": {
        "ru": "Рефлексия сохранена. Посмотри /report. Это не профессиональный диагноз.",
        "en": "Your reflection has been saved. View /report. This is not a professional assessment or diagnosis.",
    },
    "too_long": {
        "ru": "Сократи ответ до 300 символов.",
        "en": "Please shorten your answer to 300 characters.",
    },
}


def tr(locale: str, key: str, **kwargs: object) -> str:
    if key not in MESSAGES:
        raise KeyError(key)
    template = MESSAGES[key].get(locale, MESSAGES[key]["ru"])
    return template.format(**kwargs)
