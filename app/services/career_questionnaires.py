"""Versioned career and skills reflection questionnaires.

Exploratory prompts only; not a psychometric assessment or career diagnosis.
"""
from __future__ import annotations

from app.services.guided_reflection import Question, Session, start

QUESTIONNAIRE_VERSION = "2026.10.1"

CAREER_EXPLORATION = (
    Question("interests", "Какие занятия тебе интересны, даже если пока не всё получается?",
             "Which activities interest you, even if you are still learning?"),
    Question("experience", "Что ты уже пробовал(а) делать или создавать?",
             "What have you already tried doing or creating?"),
    Question("skills", "Какие навыки ты уже используешь на практике?",
             "Which skills do you already use in practice?"),
    Question("learning", "Чему ты хотел(а) бы научиться в ближайшее время?",
             "What would you like to learn next?"),
    Question("constraints", "Какие условия важно учитывать: время, доступные инструменты, поддержка?",
             "Which conditions matter: time, available tools, support?"),
    Question("experiment", "Какой небольшой безопасный проект ты хотел(а) бы попробовать?",
             "What small, safe project would you like to try?"),
)

SKILLS_REFLECTION = (
    Question("activity", "Какую задачу ты недавно выполнял(а)?",
             "What task have you worked on recently?"),
    Question("method", "Какие действия и инструменты ты использовал(а)?",
             "Which actions and tools did you use?"),
    Question("evidence", "По чему можно понять, что задача была выполнена?",
             "What evidence shows that the task was completed?"),
    Question("feedback", "Какую обратную связь ты получил(а), если получал(а)?",
             "What feedback, if any, did you receive?"),
    Question("growth", "Что ты хотел(а) бы попробовать улучшить в следующий раз?",
             "What would you like to improve next time?"),
)

QUESTIONNAIRES = {
    "career": CAREER_EXPLORATION,
    "skills": SKILLS_REFLECTION,
}


def begin_questionnaire(name: str) -> Session:
    if name not in QUESTIONNAIRES:
        raise ValueError("Unknown questionnaire")
    return start(QUESTIONNAIRES[name])
