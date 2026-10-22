"""Minimal Telegram long-polling runner for Yugatneo BOT.

Run locally with: python -m app.telegram_polling
Secrets belong in .env and must never be committed.
"""
import asyncio
import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.models import Channel, IncomingMessage
from app.services.dialogue import respond
from app.services.question_catalog import QuestionCatalog
from app.services.branching_dialogue import NODES, advance, options
from app.services.question_adaptation import DialoguePreferences, topic_allowed, adapt_question, voluntary_intro
from app.services.safety import classify_crisis_message, crisis_response
from app.services.diagnostic_flow import handle_diagnostic_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "yugatneo_bot.sqlite3"
MENU = {
    "keyboard": [
        [{"text": "🧭 Колесо баланса"}, {"text": "📊 Мои оценки"}],
        [{"text": "💬 Рефлексия"}, {"text": "📚 Вопросы"}],
        [{"text": "🌿 Диалог по ответам"}],
        [{"text": "🧩 Настроить вопросы"}, {"text": "⚙️ Удобство диалога"}],
        [{"text": "❔ Помощь"}],
    ],
    "resize_keyboard": True,
}
CATALOG = QuestionCatalog()
CANCEL_WORDS = {"/cancel", "отмена", "стоп", "назад"}


def available_question_categories(prefs: DialoguePreferences | None = None) -> dict[str, str]:
    """Russian display label -> stable category ID, only for safe offline topics."""
    prefs = prefs or DialoguePreferences()
    return {
        next(q.subcategory for q in CATALOG.questions if q.category == category): category
        for category in CATALOG.categories()
        if topic_allowed(category, prefs) and any(q.category == category and q.risk_level == "standard" for q in CATALOG.questions)
    }


def question_keyboard(prefs: DialoguePreferences | None = None) -> dict:
    labels = list(available_question_categories(prefs))
    return {
        "keyboard": [[{"text": label}] for label in labels]
                    + [[{"text": "↩️ Главное меню"}]],
        "resize_keyboard": True,
    }



def branch_keyboard(node_id: str) -> dict:
    return {"keyboard": [[{"text": label}] for label in options(node_id)]
            + [[{"text": "↩️ Главное меню"}]], "resize_keyboard": True}


def branch_prompt(node_id: str) -> str:
    return NODES[node_id].prompt + (
        "\\n\\nВыбери ответ кнопкой, либо заверши сценарий через /cancel."
        if options(node_id) else
        "\\n\\nМожно свободно обдумать вопрос. /cancel — выход. "
        "Для другого сценария выбери «🌿 Диалог по ответам»."
    )


def read_prefs(user_id: str) -> DialoguePreferences:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT age_group, format, chronic_health_topic, sensitive_opt_in "
            "FROM dialogue_preferences WHERE telegram_user_id=?", (user_id,)
        ).fetchone()
    if row is None:
        return DialoguePreferences()
    return DialoguePreferences(age_group=row[0], format=row[1],
                               chronic_health_topic=bool(row[2]),
                               sensitive_opt_in=bool(row[3]))


def save_prefs(user_id: str, prefs: DialoguePreferences) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO dialogue_preferences VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(telegram_user_id) DO UPDATE SET "
            "age_group=excluded.age_group, format=excluded.format, "
            "chronic_health_topic=excluded.chronic_health_topic, "
            "sensitive_opt_in=excluded.sensitive_opt_in",
            (user_id, prefs.age_group, prefs.format, int(prefs.chronic_health_topic),
             int(prefs.sensitive_opt_in))
        )


def preference_keyboard() -> dict:
    return {"keyboard": [
        [{"text": "Взрослый"}, {"text": "Подросток"}, {"text": "Старший возраст"}],
        [{"text": "Короткие вопросы"}, {"text": "Обычные вопросы"}],
        [{"text": "Обсудить хроническое состояние"}],
        [{"text": "Разрешить глубокую рефлексию"}],
        [{"text": "Сбросить предпочтения"}, {"text": "↩️ Главное меню"}],
    ], "resize_keyboard": True}


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wheel_scores (
                telegram_user_id TEXT NOT NULL,
                sphere TEXT NOT NULL,
                score INTEGER NOT NULL CHECK(score BETWEEN 0 AND 10),
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (telegram_user_id, sphere)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dialogue_preferences (
                telegram_user_id TEXT PRIMARY KEY,
                age_group TEXT NOT NULL DEFAULT 'unknown',
                format TEXT NOT NULL DEFAULT 'standard',
                chronic_health_topic INTEGER NOT NULL DEFAULT 0,
                sensitive_opt_in INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_state (
                telegram_user_id TEXT PRIMARY KEY,
                mode TEXT NOT NULL,
                sphere TEXT
            )
        """)


def set_state(user_id: str, mode: str, sphere: str | None = None) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO bot_state(telegram_user_id, mode, sphere) VALUES (?, ?, ?) "
            "ON CONFLICT(telegram_user_id) DO UPDATE SET mode=excluded.mode, sphere=excluded.sphere",
            (user_id, mode, sphere),
        )


def get_state(user_id: str) -> tuple[str, str | None]:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT mode, sphere FROM bot_state WHERE telegram_user_id=?", (user_id,)
        ).fetchone()
    return (row[0], row[1]) if row else ("menu", None)


def save_score(user_id: str, sphere: str, score: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO wheel_scores(telegram_user_id, sphere, score) VALUES (?, ?, ?) "
            "ON CONFLICT(telegram_user_id, sphere) DO UPDATE SET "
            "score=excluded.score, updated_at=CURRENT_TIMESTAMP",
            (user_id, sphere, score),
        )


def get_scores(user_id: str) -> list[tuple[str, int]]:
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            "SELECT sphere, score FROM wheel_scores WHERE telegram_user_id=? ORDER BY sphere",
            (user_id,),
        ).fetchall()


async def api(client: httpx.AsyncClient, token: str, method: str, payload: dict[str, Any] | None = None) -> Any:
    response = await client.post(f"https://api.telegram.org/bot{token}/{method}", json=payload or {})
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API {method} failed")
    return data["result"]


async def send(client: httpx.AsyncClient, token: str, chat_id: int, text: str, keyboard: dict | None = MENU) -> None:
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text[:4000]}
    if keyboard is not None:
        payload["reply_markup"] = keyboard
    await api(client, token, "sendMessage", payload)


async def handle_message(client: httpx.AsyncClient, token: str, message: dict[str, Any]) -> None:
    user = message.get("from") or {}
    chat = message.get("chat") or {}
    if not user.get("id") or not chat.get("id"):
        return
    user_id = str(user["id"])
    chat_id = int(chat["id"])
    text = (message.get("text") or "").strip()
    if not text:
        await send(client, token, chat_id, "Пока я обрабатываю только текстовые сообщения. Голосовые заметки добавим отдельным этапом.")
        return

    # Safety takes precedence over every scripted flow, not just LLM reflection.
    crisis = classify_crisis_message(text)
    if crisis:
        set_state(user_id, "menu")
        await send(client, token, chat_id, crisis_response(crisis), MENU)
        return

    if text.lower() in CANCEL_WORDS:
        set_state(user_id, "menu")
        await send(client, token, chat_id, "Остановил текущий сценарий. Выбирай, что делать дальше.", MENU)
        return

    if text.startswith("/start"):
        set_state(user_id, "menu")
        await send(
            client, token, chat_id,
            "Привет! Я Yugatn Neo Symbiot — помощник для коучинга, самоисследования и психообразования.\n\n"
            "Можно пропустить любой вопрос или остановиться. Я не ставлю диагнозы и не заменяю специалиста. "
            "Не отправляй пароли и данные, которые не хочешь передавать сервису.\n\n"
            "Выбери «Колесо баланса» для субъективной оценки сфер жизни от 0 до 10 или «Рефлексия» для диалога. «Вопросы» и «Диалог по ответам» работают без ИИ.",
            MENU,
        )
        return

    if text == "❔ Помощь" or text == "/help":
        await send(client, token, chat_id, "Команды: /start — меню; /questions — библиотека вопросов; /skip — пропустить вопрос; /cancel — остановить сценарий. Оценки колеса субъективны и не являются диагностикой.", MENU)
        return

    if text == "🧭 Колесо баланса":
        set_state(user_id, "wheel_name")
        await send(
            client, token, chat_id,
            "Начнём колесо баланса. Назови сферу жизни своими словами (например, «здоровье», «творчество» или «отношения»). "
            "Я не навязываю готовый список. После названия попрошу оценку от 0 до 10. "
            "Можно добавлять сферы по одной; /cancel — выход.",
            MENU,
        )
        return

    if text == "📊 Мои оценки":
        scores = get_scores(user_id)
        if not scores:
            await send(client, token, chat_id, "Пока оценок нет. Нажми «Колесо баланса», чтобы добавить первую сферу.", MENU)
        else:
            lines = ["Твои последние оценки (0–10):"] + [f"• {sphere}: {score}/10" for sphere, score in scores]
            lines.append("\nЭто субъективный снимок на текущий момент, а не диагноз и не рейтинг.")
            await send(client, token, chat_id, "\n".join(lines), MENU)
        return

    if text == "🧩 Настроить вопросы":
        text = "/diagnostic"

    if text.lower() in {"/diagnostic", "диагностика", "/diagnostic_reset",
                        "/skip_diagnostic", "пропустить диагностику",
                        "сбросить диагностику", "/question_order", "порядок вопросов"}:
        try:
            result = handle_diagnostic_message("telegram", user_id, text)
            if result:
                status = result.get("metadata", {}).get("diagnostic")
                set_state(user_id, "diagnostic" if status in {"started", "in_progress", "awaiting_valid_answer"} else "menu")
                await send(client, token, chat_id, result["text"], MENU)
                return
        except Exception:
            log.exception("Onboarding failed")
            await send(client, token, chat_id, "Не получилось продолжить анкету. Можно пропустить её командой /skip_diagnostic.")
            return

    if text == "💬 Рефлексия":
        set_state(user_id, "reflection")
        await send(client, token, chat_id, "С чего тебе хотелось бы начать? Что сейчас важнее всего понять или изменить? Можешь ответить свободно; /cancel — выход.", MENU)
        return

    if text == "↩️ Главное меню":
        set_state(user_id, "menu")
        await send(client, token, chat_id, "Главное меню.", MENU)
        return

    if text in {"🌿 Диалог по ответам", "/branch"}:
        set_state(user_id, "branch:start")
        await send(client, token, chat_id, branch_prompt("start"),
                   branch_keyboard("start"))
        return

    if text == "⚙️ Удобство диалога" or text == "/preferences":
        set_state(user_id, "preferences")
        await send(client, token, chat_id, voluntary_intro()
                   + "\\n\\nВыбери только те настройки, которые хочешь сообщить. "
                   "Они меняют подбор тем, но не являются оценкой личности.",
                   preference_keyboard())
        return

    if text == "📚 Вопросы" or text == "/questions":
        set_state(user_id, "question_category")
        await send(
            client, token, chat_id,
            "Выбери тему кнопкой ниже. Эти вопросы работают без подключения к ИИ.\n\n"
            "Можно пропустить любой вопрос: /skip. Завершить: /cancel.\n"
            "Для чувствительных тем автоматический сценарий пока отключён.",
            question_keyboard(read_prefs(user_id)),
        )
        return

    mode, sphere = get_state(user_id)
    if mode in {"reflection", "diagnostic"}:
        try:
            result = handle_diagnostic_message("telegram", user_id, text)
            if result:
                status = result.get("metadata", {}).get("diagnostic")
                if mode == "diagnostic":
                    set_state(user_id, "diagnostic" if status in {"started", "in_progress", "awaiting_valid_answer"} else "reflection")
                await send(client, token, chat_id, result["text"], MENU)
                return
        except Exception:
            log.exception("Adaptive onboarding failed")
        if mode == "diagnostic":
            await send(client, token, chat_id, "Не удалось обработать ответ. Напиши /skip_diagnostic для выхода.")
            return

    if mode.startswith("branch:"):
        node_id = mode.split(":", 1)[1]
        if node_id not in NODES:
            set_state(user_id, "menu")
            await send(client, token, chat_id, "Сценарий устарел. Начни заново.", MENU)
            return
        next_id = advance(node_id, text)
        if next_id is not None:
            set_state(user_id, "branch:" + next_id)
            await send(client, token, chat_id, branch_prompt(next_id),
                       branch_keyboard(next_id) if options(next_id) else MENU)
        elif options(node_id):
            await send(client, token, chat_id,
                       "Выбери вариант кнопкой. Если ни один не подходит, "
                       "можно выйти и воспользоваться свободной рефлексией.",
                       branch_keyboard(node_id))
        else:
            await send(client, token, chat_id,
                       "Спасибо за ответ. Это вопрос для самостоятельного "
                       "осмысления, а не оценка личности. Можно перейти к "
                       "свободной рефлексии через главное меню.", MENU)
            set_state(user_id, "menu")
        return

    if mode == "preferences":
        prefs = read_prefs(user_id)
        from dataclasses import replace
        if text in {"Взрослый", "Подросток", "Старший возраст"}:
            prefs = replace(prefs, age_group={
                "Взрослый": "adult", "Подросток": "under_18",
                "Старший возраст": "older_adult"}[text])
        elif text in {"Короткие вопросы", "Обычные вопросы"}:
            prefs = replace(prefs, format="short" if text == "Короткие вопросы" else "standard")
        elif text == "Обсудить хроническое состояние":
            prefs = replace(prefs, chronic_health_topic=not prefs.chronic_health_topic)
        elif text == "Разрешить глубокую рефлексию":
            prefs = replace(prefs, sensitive_opt_in=not prefs.sensitive_opt_in)
        elif text == "Сбросить предпочтения":
            prefs = DialoguePreferences()
        else:
            await send(client, token, chat_id, "Выбери настройку кнопкой.",
                       preference_keyboard())
            return
        if prefs.age_group == "under_18":
            prefs = replace(prefs, sensitive_opt_in=False)
        save_prefs(user_id, prefs)
        await send(client, token, chat_id,
                   "Предпочтения обновлены. Можно менять их в любой момент. "
                   "Бот не сохраняет диагнозы и подробные истории заболеваний.",
                   preference_keyboard())
        return

    if mode == "question_category":
        categories = available_question_categories(read_prefs(user_id))
        category = categories.get(text)
        if category is None:
            await send(client, token, chat_id,
                       "Выбери тему с помощью кнопок или отправь /cancel.",
                       question_keyboard(read_prefs(user_id)))
            return
        eligible = [q for q in CATALOG.questions
                    if q.category == category and q.risk_level == "standard"]
        set_state(user_id, "questions:0", category)
        await send(client, token, chat_id,
                   f"Вопрос 1/{len(eligible)}\n\n{adapt_question(eligible[0].text, read_prefs(user_id))}\n\n"
                   "Ответ не сохраняется. /skip — следующий, /cancel — завершить.",
                   {"keyboard": [[{"text": "/skip"}, {"text": "/cancel"}]],
                    "resize_keyboard": True})
        return

    if mode.startswith("questions:"):
        category = sphere or ""
        eligible = [q for q in CATALOG.questions
                    if q.category == category and q.risk_level == "standard"]
        try:
            index = int(mode.split(":", 1)[1]) + 1
        except (IndexError, ValueError):
            index = len(eligible)
        if index >= len(eligible):
            set_state(user_id, "menu")
            await send(client, token, chat_id,
                       "Эта серия завершена. Ответы не сохранялись. Можно выбрать другую тему.",
                       MENU)
        else:
            set_state(user_id, f"questions:{index}", category)
            await send(client, token, chat_id,
                       f"Вопрос {index + 1}/{len(eligible)}\n\n"
                       + adapt_question(eligible[index].text, read_prefs(user_id))
                       + "\n\nОтвет не сохраняется. /skip — следующий, /cancel — завершить.")
        return

    if mode == "wheel_name":
        sphere = re.sub(r"\s+", " ", text).strip()[:80]
        if not sphere:
            await send(client, token, chat_id, "Напиши название сферы или /cancel.")
            return
        set_state(user_id, "wheel_score", sphere)
        await send(client, token, chat_id, f"Как ты оцениваешь сферу «{sphere}» сейчас от 0 до 10? Это только твоя субъективная оценка.")
        return

    if mode == "wheel_score":
        if not re.fullmatch(r"(10|[0-9])", text):
            await send(client, token, chat_id, "Введи целое число от 0 до 10. Для выхода — /cancel.", None)
            return
        score = int(text)
        save_score(user_id, sphere or "Без названия", score)
        set_state(user_id, "wheel_name")
        await send(client, token, chat_id, f"Сохранил: {sphere} — {score}/10.\nНазови следующую сферу или отправь /cancel, чтобы закончить.", MENU)
        return

    if mode == "reflection":
        incoming = IncomingMessage(
            channel=Channel.TELEGRAM,
            external_user_id=user_id,
            text=text,
            message_id=str(message.get("message_id", "")) or None,
        )
        try:
            reply = await respond(incoming)
            await send(client, token, chat_id, reply.text, MENU)
        except Exception:
            log.exception("Reflection response failed")
            await send(client, token, chat_id, "Не удалось подготовить ответ. Попробуй ещё раз чуть позже.", MENU)
        return

    set_state(user_id, "menu")
    await send(client, token, chat_id, "Выбери действие в меню. Если хочешь начать заново, отправь /start.", MENU)


async def main() -> None:
    settings = get_settings()
    token = settings.telegram_bot_token
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN не задан. Добавь токен в локальный .env; не публикуй его в GitHub или чате.")
    init_db()
    offset: int | None = None
    timeout = httpx.Timeout(40.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        me = await api(client, token, "getMe")
        log.info("Polling started for @%s. Stop with Ctrl+C.", me.get("username", "bot"))
        while True:
            params: dict[str, Any] = {"timeout": 30, "allowed_updates": ["message"]}
            if offset is not None:
                params["offset"] = offset
            try:
                updates = await api(client, token, "getUpdates", params)
                for update in updates:
                    offset = update["update_id"] + 1
                    if update.get("message"):
                        await handle_message(client, token, update["message"])
            except (httpx.HTTPError, RuntimeError):
                log.exception("Telegram polling error; retrying in 3 seconds")
                await asyncio.sleep(3)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot stopped by user.")
