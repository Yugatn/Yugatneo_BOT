"""Persistent, minimal onboarding flow for adaptive question selection.

Stores only the current diagnostic answers and profile per channel identity.
It is a navigation aid, not a clinical screening instrument.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.models import Question
from app.services.catalog import load_questions
from app.services.diagnostic import DiagnosticProfile, prioritize_questions
from app.services.sqlite_security import secure_sqlite_path, secure_sqlite_sidecars
from app.services.diagnostic_encryption import encrypt_diagnostic_json, decrypt_diagnostic_json

STEPS = ["age", "goal", "distress", "style", "temperament", "gender", "psychotype"]
GOAL_LABELS = {
    "emotions": "Эмоции и состояние",
    "anxiety": "Тревога и неопределённость",
    "relationships": "Отношения и границы",
    "goals": "Цели и решения",
    "identity": "Идентичность и самоотношение",
    "conditioning": "Обусловленность и автоматические сценарии",
    "work": "Работа и профессиональное развитие",
    "general": "Пока не определился",
}
STYLE_LABELS = {
    "structured": "Структурированный",
    "open": "Открытый",
    "direct": "Прямой",
    "gentle": "Бережный",
    "unsure": "Не уверен",
}
TEMPERAMENT_LABELS = {
    "sanguine": "Сангвиник (самоописание)",
    "choleric": "Холерик (самоописание)",
    "phlegmatic": "Флегматик (самоописание)",
    "melancholic": "Меланхолик (самоописание)",
    "unsure": "Не уверен / не хочу определять",
}


def _db_path() -> str:
    url = get_settings().database_url
    if not url.startswith("sqlite:///"):
        raise RuntimeError("Diagnostic flow currently supports SQLite URLs only")
    return url.removeprefix("sqlite:///")


def _connect() -> sqlite3.Connection:
    path = _db_path()
    if path != ":memory:":
        secure_sqlite_path(path)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute("""CREATE TABLE IF NOT EXISTS diagnostic_sessions (
        subject_key TEXT PRIMARY KEY,
        step_index INTEGER NOT NULL,
        answers_json TEXT NOT NULL,
        completed INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    if path != ":memory:":
        secure_sqlite_sidecars(path)
    return conn


def _subject_key(channel: str, external_user_id: str) -> str:
    return hashlib.sha256(f"{channel}:{external_user_id}".encode("utf-8")).hexdigest()


def _read(channel: str, external_user_id: str) -> dict[str, Any] | None:
    conn = _connect()
    try:
        key = _subject_key(channel, external_user_id)
        row = conn.execute(
            "SELECT step_index, answers_json, completed, updated_at FROM diagnostic_sessions WHERE subject_key=?",
            (key,),
        ).fetchone()
        if not row:
            return None
        # Delete abandoned onboarding/profile data after 30 days of inactivity.
        if conn.execute("SELECT datetime(?) < datetime('now', '-30 days')", (row[3],)).fetchone()[0]:
            conn.execute("DELETE FROM diagnostic_sessions WHERE subject_key=?", (key,))
            conn.commit()
            return None
        return {"step_index": row[0], "answers": json.loads(decrypt_diagnostic_json(row[1])), "completed": bool(row[2])}
    finally:
        conn.close()


def _write(channel: str, external_user_id: str, step_index: int, answers: dict[str, Any], completed: bool = False) -> None:
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO diagnostic_sessions(subject_key, step_index, answers_json, completed, updated_at)
               VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(subject_key) DO UPDATE SET step_index=excluded.step_index,
               answers_json=excluded.answers_json, completed=excluded.completed, updated_at=CURRENT_TIMESTAMP""",
            (_subject_key(channel, external_user_id), step_index, encrypt_diagnostic_json(json.dumps(answers, ensure_ascii=False)), int(completed)),
        )
        conn.commit()
    finally:
        conn.close()


def clear_diagnostic(channel: str, external_user_id: str) -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM diagnostic_sessions WHERE subject_key=?", (_subject_key(channel, external_user_id),))
        conn.commit()
    finally:
        conn.close()


def _prompt(step: str) -> tuple[str, list[dict[str, str]]]:
    if step == "age":
        return "Сколько тебе лет? Укажи число. Возраст нужен только для выбора подходящего формата вопросов.", []
    if step == "goal":
        return "С какой темой хочешь начать? Можно пропустить диагностику командой «пропустить».", [
            {"label": label, "value": f"diagnostic:goal:{key}"} for key, label in GOAL_LABELS.items()
        ]
    if step == "distress":
        return "Насколько сильное напряжение ты чувствуешь прямо сейчас? Это твоя субъективная оценка, не диагноз.", [
            {"label": "0 — спокойно", "value": "diagnostic:distress:0"},
            {"label": "1 — небольшое", "value": "diagnostic:distress:1"},
            {"label": "2 — заметное", "value": "diagnostic:distress:2"},
            {"label": "3 — сильное", "value": "diagnostic:distress:3"},
            {"label": "4 — очень сильное", "value": "diagnostic:distress:4"},
        ]
    if step == "style":
        return "Как тебе удобнее разговаривать?", [
            {"label": label, "value": f"diagnostic:style:{key}"} for key, label in STYLE_LABELS.items()
        ]
    if step == "temperament":
        return "Хочешь указать свой темперамент? Это необязательное самоописание, а не научная диагностика.", [
            {"label": label, "value": f"diagnostic:temperament:{key}"} for key, label in TEMPERAMENT_LABELS.items()
        ]
    if step == "gender":
        return "Гендер указывать необязательно. Он не влияет на психологическую оценку. Напиши «пропустить» или своё самоописание.", []
    if step == "psychotype":
        return "Если хочешь, опиши свой психотип своими словами (например, «аналитический» или «ориентирован на действие»). Это необязательное самоописание. Можно написать «пропустить».", []
    raise ValueError("Unknown diagnostic step")


def start_diagnostic(channel: str, external_user_id: str) -> dict[str, Any]:
    _write(channel, external_user_id, 0, {"goal": "general", "distress": 1, "urgency": "normal",
                                           "style": "unsure", "temperament": "unsure",
                                           "gender": None, "psychotype": "unsure"})
    text, buttons = _prompt(STEPS[0])
    return {"text": "Давай настроим порядок вопросов. Это займёт около минуты. Можно пропустить любой пункт или остановиться. Ответы используются для настройки диалога.\n\n" + text, "buttons": buttons, "metadata": {"diagnostic": "started"}}


def _parse(step: str, text: str) -> Any:
    value = text.strip()
    lowered = value.casefold()
    if lowered in {"/skip", "skip", "пропустить", "пропуск", "не хочу", "не указывать"}:
        return None
    parts = value.split(":")
    if len(parts) == 3 and parts[0] == "diagnostic" and parts[1] == step:
        value = parts[2]
        lowered = value.casefold()
    if step == "age":
        try:
            age = int(value)
        except ValueError as exc:
            raise ValueError("Напиши возраст числом или «пропустить» для настройки без возрастной группы.") from exc
        if not 1 <= age <= 120:
            raise ValueError("Возраст должен быть числом от 1 до 120.")
        return age
    if step == "goal":
        aliases = {"эмоции": "emotions", "тревога": "anxiety", "отношения": "relationships",
                   "цели": "goals", "идентичность": "identity", "обусловленность": "conditioning",
                   "работа": "work", "общее": "general"}
        key = aliases.get(lowered, lowered)
        if key not in GOAL_LABELS:
            raise ValueError("Выбери тему кнопкой или напиши: эмоции, тревога, отношения, цели, идентичность, обусловленность, работа, общее.")
        return key
    if step == "distress":
        try:
            score = int(value)
        except ValueError as exc:
            raise ValueError("Выбери число от 0 до 4.") from exc
        if not 0 <= score <= 4:
            raise ValueError("Выбери число от 0 до 4.")
        return score
    if step == "style":
        if lowered not in STYLE_LABELS:
            raise ValueError("Выбери стиль кнопкой или напиши: structured, open, direct, gentle, unsure.")
        return lowered
    if step == "temperament":
        if lowered not in TEMPERAMENT_LABELS:
            aliases = {"сангвиник": "sanguine", "холерик": "choleric", "флегматик": "phlegmatic",
                       "меланхолик": "melancholic", "не уверен": "unsure"}
            lowered = aliases.get(lowered, lowered)
        if lowered not in TEMPERAMENT_LABELS:
            raise ValueError("Выбери вариант кнопкой или напиши один из четырёх темпераментов либо «не уверен».")
        return lowered
    if step == "gender":
        return None if value == "" else value[:80]
    if step == "psychotype":
        return "unsure" if value == "" else value[:80]
    raise ValueError("Unknown diagnostic step")


def _profile(answers: dict[str, Any]) -> DiagnosticProfile:
    return DiagnosticProfile(
        age=answers.get("age") or 30,
        gender=answers.get("gender"),
        temperament=answers.get("temperament") or "unsure",
        psychotype=answers.get("psychotype") or "unsure",
        goal=answers.get("goal") or "general",
        distress=answers.get("distress", 1),
        urgency=answers.get("urgency", "normal"),
        style=answers.get("style") or "unsure",
    )


def _recommend(answers: dict[str, Any]) -> dict[str, Any]:
    return prioritize_questions(load_questions(), _profile(answers), limit=12)


def _adaptive_goal(text: str, current_goal: str) -> str:
    lowered = text.casefold()
    rules = {
        "relationships": ("партнёр", "партнер", "отношен", "семь", "друг", "конфликт", "границ"),
        "anxiety": ("тревог", "страш", "паник", "неопредел", "боюсь", "беспоко"),
        "work": ("работ", "карьер", "начальник", "коллег", "професс"),
        "goals": ("цель", "решен", "мотивац", "прокраст", "привыч"),
        "conditioning": ("обусловлен", "ожидани", "установк", "автоматическ", "сценари", "навязан"),
        "identity": ("кто я", "идентич", "самооцен", "себя", "ценност"),
        "emotions": ("эмоци", "злость", "гнев", "грусть", "одиночеств", "устал"),
    }
    for goal, terms in rules.items():
        if any(term in lowered for term in terms):
            return goal
    return current_goal


def handle_diagnostic_message(channel: str, external_user_id: str, text: str) -> dict[str, Any] | None:
    """Handle one diagnostic answer; after onboarding return the first tailored reflection question."""
    session = _read(channel, external_user_id)
    if text.strip().casefold() in {"/diagnostic", "диагностика", "настроить вопросы", "начать диагностику"}:
        return start_diagnostic(channel, external_user_id)
    if text.strip().casefold() in {"согласен", "согласна", "да, согласен", "да, согласна", "i agree"} and (not session or session["completed"]):
        return start_diagnostic(channel, external_user_id)
    if text.strip().casefold() in {"/diagnostic_reset", "сбросить диагностику"}:
        clear_diagnostic(channel, external_user_id)
        return {"text": "Настройки диагностики удалены. Напиши «диагностика», чтобы начать заново.", "metadata": {"diagnostic": "reset"}}
    if text.strip().casefold() in {"/skip_diagnostic", "пропустить диагностику", "отмена диагностики"}:
        clear_diagnostic(channel, external_user_id)
        return {"text": "Хорошо, пропускаем анкету. Можешь сразу написать, что хочешь обсудить.", "metadata": {"diagnostic": "skipped"}}
    if text.strip().casefold() in {"порядок вопросов", "какие вопросы дальше", "/question_order"}:
        recommendation = recommendation_for(channel, external_user_id)
        if not recommendation:
            return {"text": "Сначала можно настроить порядок вопросов командой «диагностика». Это необязательно.", "metadata": {"diagnostic": "not_configured"}}
        questions = recommendation.get("questions", [])
        lines = [f"{index + 1}. {item['text']}" for index, item in enumerate(questions[:5])]
        return {"text": "Ближайшие рекомендованные вопросы (это ориентир, не обязательная программа):\\n" + "\\n".join(lines), "metadata": {"diagnostic": "recommendation_shown"}}
    if text.strip().casefold() in {"сменить тему", "изменить настройки", "перенастроить вопросы"}:
        return start_diagnostic(channel, external_user_id)
    if not session or session["completed"]:
        return None
    step = STEPS[session["step_index"]]
    try:
        parsed = _parse(step, text)
    except ValueError as exc:
        prompt, buttons = _prompt(step)
        return {"text": f"{exc}\n\n{prompt}", "buttons": buttons, "metadata": {"diagnostic": "awaiting_valid_answer", "step": step}}

    answers = session["answers"]
    if parsed is not None:
        answers[step] = parsed
    if step == "age" and parsed is None:
        answers["age"] = 30
    next_index = session["step_index"] + 1
    if next_index < len(STEPS):
        _write(channel, external_user_id, next_index, answers)
        next_step = STEPS[next_index]
        prompt, buttons = _prompt(next_step)
        buttons = buttons + [{"label": "Пропустить анкету", "value": "пропустить диагностику"}]
        return {"text": prompt, "buttons": buttons, "metadata": {"diagnostic": "in_progress", "step": next_step}}

    result = _recommend(answers)
    # Do not retain free-text gender/psychotype after they have served as optional onboarding inputs.
    # Exact age is reduced to a representative value for the same broad age band.
    age = answers.get("age", 30)
    answers["age"] = 17 if age < 18 else 24 if age < 30 else 37 if age < 45 else 52 if age < 60 else 65
    answers["gender"] = None
    answers["psychotype"] = "unsure"
    result["profile_used"]["psychotype_self_report"] = "unsure"
    answers["recommendation"] = result
    answers["current_goal"] = answers.get("goal", "general")
    answers["turns_since_replan"] = 0
    _write(channel, external_user_id, len(STEPS), answers, completed=True)
    first = result["questions"][0]
    return {
        "text": (
            "Готово. Это не диагноз: я лишь подобрал предварительный порядок тем. "
            "Ты можешь в любой момент изменить тему или попросить новый порядок.\n\n"
            f"Начнём с вопроса:\n{first['text']}\n\n"
            "Команды: «сменить тему», «порядок вопросов», «сбросить диагностику»."
        ),
        "buttons": [
            {"label": "Эмоции", "value": "topic:emotions"},
            {"label": "Цели", "value": "topic:goals"},
            {"label": "Отношения", "value": "topic:relationships"},
            {"label": "Изменить порядок", "value": "/diagnostic"},
        ],
        "metadata": {"diagnostic": "completed", "first_question_id": first["id"],
                     "first_category": first["category"], "recommended_count": len(result["questions"])},
    }


def adaptive_context(channel: str, external_user_id: str, user_text: str) -> str:
    """Update the preferred theme from explicit language cues and return minimal context for the LLM."""
    session = _read(channel, external_user_id)
    if not session or not session["completed"]:
        return ""
    answers = session["answers"]
    current_goal = answers.get("current_goal", answers.get("goal", "general"))
    new_goal = _adaptive_goal(user_text, current_goal)
    changed = new_goal != current_goal
    if changed:
        answers["current_goal"] = new_goal
    turns = int(answers.get("turns_since_replan", 0)) + 1
    if changed or turns >= 3:
        answers["recommendation"] = _recommend({**answers, "goal": new_goal})
        turns = 0
    answers["turns_since_replan"] = turns
    _write(channel, external_user_id, len(STEPS), answers, completed=True)
    recommendation = answers.get("recommendation") or _recommend(answers)
    first = recommendation["questions"][0]
    return (
        "Контекст навигации Yugatneo BOT (не диагноз): "
        f"тема пользователя сейчас — {new_goal}; предпочтительный стиль — {answers.get('style', 'unsure')}; "
        f"самооценка напряжения при старте — {answers.get('distress', 1)}/4. "
        f"Предпочтительные следующие темы: {', '.join(recommendation['first_categories'][:4])}. "
        f"Подходящий рефлексивный вопрос из каталога: {first['text']}. "
        "Отвечай на последнее сообщение пользователя естественно, задавай по одному вопросу, "
        "не навязывай каталог и уточняй смену цели, если это неоднозначно."
    )


def recommendation_for(channel: str, external_user_id: str) -> dict[str, Any] | None:
    session = _read(channel, external_user_id)
    if not session or not session["completed"]:
        return None
    return session["answers"].get("recommendation")
