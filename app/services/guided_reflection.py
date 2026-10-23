"""Channel-independent, privacy-first guided reflection engine.

Sessions are immutable and remain in memory of the calling application.
Persisting or exporting answers requires a separate explicit opt-in workflow.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

AnswerKind = Literal["text", "scale"]
MAX_ANSWER = 1000


@dataclass(frozen=True)
class Question:
    id: str
    ru: str
    en: str
    kind: AnswerKind = "text"
    optional: bool = True


@dataclass(frozen=True)
class Response:
    question_id: str
    value: str | None


@dataclass(frozen=True)
class Session:
    questions: tuple[Question, ...]
    responses: tuple[Response, ...] = ()
    finished: bool = False

    @property
    def current(self) -> Question | None:
        if self.finished or len(self.responses) >= len(self.questions):
            return None
        return self.questions[len(self.responses)]


CORE_REFLECTION = (
    Question("goal", "Что ты хотел(а) бы изменить или развить?", "What would you like to change or develop?"),
    Question("strength", "Что у тебя уже получается?", "What is already working well?"),
    Question("obstacle", "Что сейчас затрудняет движение к цели?", "What makes progress difficult right now?"),
    Question("resource", "Какая поддержка или ресурс могли бы помочь?", "What support or resource could help?"),
    Question("step", "Какой небольшой шаг ты готов(а) попробовать?", "What small step would you like to try?"),
)


def start(questions: tuple[Question, ...] = CORE_REFLECTION) -> Session:
    if not questions or len({q.id for q in questions}) != len(questions):
        raise ValueError("Questions must be nonempty and have unique IDs")
    return Session(questions=questions)


def advance(session: Session, answer: str | None) -> Session:
    question = session.current
    if question is None:
        raise ValueError("Session already completed")
    value = answer.strip() if answer is not None else None
    if value == "":
        value = None
    if value is None and not question.optional:
        raise ValueError("This question cannot be skipped")
    if value is not None and len(value) > MAX_ANSWER:
        raise ValueError("Answer too long")
    if value is not None and question.kind == "scale":
        if not value.isdigit() or not 0 <= int(value) <= 10:
            raise ValueError("Scale answer must be between 0 and 10")
    responses = session.responses + (Response(question.id, value),)
    return replace(session, responses=responses, finished=len(responses) == len(session.questions))


def summary(session: Session, locale: str = "ru") -> str:
    """Only repeat explicitly supplied answers; do not invent diagnoses or traits."""
    if not session.finished:
        raise ValueError("Finish or skip all questions before summary")
    if locale not in {"ru", "en"}:
        raise ValueError("Unsupported locale")
    heading = "Итог твоей рефлексии" if locale == "ru" else "Your reflection summary"
    skipped = "Пропущено" if locale == "ru" else "Skipped"
    lines = [heading]
    for question, response in zip(session.questions, session.responses):
        label = question.ru if locale == "ru" else question.en
        lines.append(f"• {label}\n  {response.value if response.value is not None else skipped}")
    lines.append(
        "Это краткое изложение твоих ответов, а не психологический диагноз."
        if locale == "ru" else
        "This is a summary of your answers, not a psychological diagnosis."
    )
    return "\n\n".join(lines)
