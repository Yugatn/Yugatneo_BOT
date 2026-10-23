"""Deterministic, opt-in coaching session state machine.

Pure functions: no network, no model calls, no sensitive raw answers in logs.
The channel adapter must store state per user and enforce consent/deletion.
"""
from dataclasses import dataclass, replace
from enum import Enum


class Stage(str, Enum):
    CONSENT = "consent"
    GOAL = "goal"
    EVIDENCE = "evidence"
    OPTIONS = "options"
    ACTION = "action"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


PROMPTS = {
    Stage.CONSENT: "Это добровольная рефлексия, не диагностика. Начать? (да/нет)",
    Stage.GOAL: "Какую конкретную цель ты выбираешь?",
    Stage.EVIDENCE: "Что ты уже наблюдал? Что пока лишь предположение?",
    Stage.OPTIONS: "Назови два возможных действия, включая право ничего не менять.",
    Stage.ACTION: "Какой один небольшой и безопасный шаг ты добровольно выбираешь?",
    Stage.REVIEW: "Когда и по какому наблюдаемому признаку ты проверишь результат?",
    Stage.DONE: "План сформирован. Его можно пересмотреть или отменить.",
    Stage.CANCELLED: "Сессия завершена без оценки и без обязательств.",
}
NEXT = {
    Stage.CONSENT: Stage.GOAL,
    Stage.GOAL: Stage.EVIDENCE,
    Stage.EVIDENCE: Stage.OPTIONS,
    Stage.OPTIONS: Stage.ACTION,
    Stage.ACTION: Stage.REVIEW,
    Stage.REVIEW: Stage.DONE,
}


@dataclass(frozen=True)
class Session:
    stage: Stage = Stage.CONSENT
    # Retain only in memory until user explicitly chooses persistence.
    answers: tuple[tuple[str, str], ...] = ()


def advance(session: Session, answer: str) -> tuple[Session, str]:
    """Return a new session and next prompt. No inferred consent."""
    answer = answer.strip()
    if session.stage in (Stage.DONE, Stage.CANCELLED):
        return session, PROMPTS[session.stage]
    if answer.casefold() in {"отмена", "/cancel", "stop", "нет, отмена"}:
        ended = Session(Stage.CANCELLED)
        return ended, PROMPTS[ended.stage]
    if session.stage is Stage.CONSENT:
        if answer.casefold() not in {"да", "yes", "согласен", "согласна"}:
            return session, PROMPTS[Stage.CONSENT]
        next_state = Session(Stage.GOAL)
        return next_state, PROMPTS[next_state.stage]
    if not answer or len(answer) > 2000:
        return session, "Ответ должен содержать от 1 до 2000 символов."
    next_stage = NEXT[session.stage]
    updated = replace(session, stage=next_stage,
                      answers=session.answers + ((session.stage.value, answer),))
    return updated, PROMPTS[next_stage]


def erase(_: Session) -> Session:
    """Explicitly discard in-memory reflections."""
    return Session(Stage.CANCELLED)
