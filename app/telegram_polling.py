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
from app.services.branching_dialogue import NODES, advance, options, question_context
from app.services.question_adaptation import DialoguePreferences, topic_allowed, adapt_question, voluntary_intro
from app.services.safety import classify_crisis_message, crisis_response
from app.services.diagnostic_flow import handle_diagnostic_message
from app.services.parenting_knowledge import TOPICS, format_topic
from app.services.parenting_index import init_index, search_index
from app.services.language_preferences import get_language, set_language, english_topic, ensure_language_table
from app.services.interface_i18n import tr
from app.services.report_formatter import build_report
from app.services.telegram_text import split_telegram_text
from app.services.bot_security import check_message, init_security
from app.services.idempotent_reflection import save_report_once
from app.services.sqlite_security import secure_sqlite_path, secure_sqlite_sidecars
from app.services.personal_data import delete_telegram_user_records
from app.services.guided_reflection import Session as GuidedSession, start as start_guided, advance as guided_advance, summary as guided_summary
from app.services.guided_report_storage import save_report as save_guided_report, read_report as read_guided_report
from app.services.reflection_action_plan import build_action_plan
from app.services.career_questionnaires import begin_questionnaire
from app.services.career_hypotheses import career_hypotheses
from app.services.safe_answer_delivery import source_bounded_answer
from app.services.diagnostic_encryption import encrypt_diagnostic_json, decrypt_diagnostic_json
from app.services.startup_security import validate_encryption_startup
from app.services.wheel_ray_catalog import catalog, normalize_ray_title
from app.services.coaching_session import Session as CoachingSession, Stage as CoachingStage, advance as coaching_advance

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "yugatneo_bot.sqlite3"
MENU = {
    "keyboard": [
        [{"text": "🧭 Колесо баланса"}, {"text": "💬 Коучинг"}],
        [{"text": "🎓 Профориентация"}, {"text": "📚 Психограмотность"}],
        [{"text": "📄 Мои результаты"}, {"text": "⚙️ Настройки"}],
    ],
    "resize_keyboard": True,
}
SUBMENUS = {
    "💬 Коучинг": [
        ["💬 Рефлексия", "🧠 Выбрать подход"],
        ["🧭 Коучинг по шагам", "📝 Рефлексия с итогом"],
        ["📚 Вопросы", "🌿 Диалог по ответам"],
        ["🧩 Настроить вопросы"],
    ],
    "🎓 Профориентация": [
        ["🎓 Навыки и профессии", "🎯 Следующий шаг"],
        ["🧭 Исследовать профессию", "🛠 Рефлексия навыков"],
    ],
    "📚 Психограмотность": [
        ["👨‍👩‍👧 Родительство", "🛡 Возрастные настройки"],
        ["📖 Источники по воспитанию"],
    ],
    "📄 Мои результаты": [
        ["📊 Мои оценки", "📈 История колеса"],
        ["📄 Мой отчёт", "✅ Отметить выполнение"],
        ["/my_guided"],
    ],
    "⚙️ Настройки": [
        ["🌐 Язык / Language", "⚙️ Удобство диалога"],
        ["❔ Помощь", "🗑 Удалить мои данные"],
    ],
}
def submenu_keyboard(name: str) -> dict:
    return {"keyboard": [[{"text": label} for label in row] for row in SUBMENUS[name]]
            + [[{"text": "↩️ Главное меню"}]], "resize_keyboard": True}

CATALOG = QuestionCatalog()
from app.services.coaching_session import PROMPTS as COACHING_PROMPTS
COACHING_SESSIONS: dict[str, CoachingSession] = {}
GUIDED_SESSIONS: dict[str, GuidedSession] = {}
GUIDED_PENDING: dict[str, str] = {}
CANCEL_WORDS = {"/cancel", "отмена", "стоп", "назад"}
APPROACHES = {
    "Гештальт-рефлексия": "Что ты замечаешь прямо сейчас: в чувствах, телесных ощущениях и потребностях? Что остаётся незавершённым и требует внимания?",
    "Коучинг": "Какую цель ты выбираешь? По каким наблюдаемым признакам поймёшь, что приблизился к ней?",
    "КПТ": "Какая мысль возникла в сложной ситуации? Какие факты подтверждают её, а какие допускают альтернативное объяснение?",
    "ACT": "Какое переживание сейчас трудно принять? Что ты можешь сделать в соответствии со своими ценностями, даже если это чувство останется?",
    "ДБТ-навыки": "Назови эмоцию и её интенсивность от 0 до 10. Что поможет безопасно снизить напряжение в ближайшие минуты?",
    "Мотивационное интервьюирование": "Что тебе хотелось бы изменить? Что удерживает от перемен и что делает их важными для тебя?",
    "Экзистенциальная рефлексия": "Какой вопрос о смысле, свободе или ответственности сейчас наиболее значим для тебя?",
}



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



def terminal_keyboard() -> dict:
    return {"keyboard": [
        [{"text": "🤖 Продолжить с ИИ"}],
        [{"text": "📚 Вопросы"}, {"text": "↩️ Главное меню"}],
    ], "resize_keyboard": True}


def branch_catalog_suggestion(node_id: str, prefs: DialoguePreferences) -> str:
    category = NODES[node_id].followup
    if not topic_allowed(category, prefs):
        return ""
    q = CATALOG.select(category)
    return ("\n\nВопрос из библиотеки для дальнейшей работы: "
            + adapt_question(q.text, prefs)) if q else ""


def branch_keyboard(node_id: str) -> dict:
    return {"keyboard": [[{"text": label}] for label in options(node_id)]
            + [[{"text": "↩️ Главное меню"}]], "resize_keyboard": True}


def branch_prompt(node_id: str) -> str:
    return NODES[node_id].prompt + (
        "\n\nВыбери ответ кнопкой, либо заверши сценарий через /cancel."
        if options(node_id) else
        "\n\nМожно свободно обдумать вопрос. /cancel — выход. "
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
        [{"text": "Сбросить предпочтения"}, {"text": "🗑 Удалить мои данные"}],
        [{"text": "↩️ Главное меню"}],
    ], "resize_keyboard": True}


def init_db() -> None:
    secure_sqlite_path(DB_PATH)
    with sqlite3.connect(DB_PATH) as conn:
        ensure_language_table(conn)
        init_security(conn)
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
            CREATE TABLE IF NOT EXISTS wheel_actions (
                telegram_user_id TEXT PRIMARY KEY,
                sphere TEXT NOT NULL,
                action TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wheel_score_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id TEXT NOT NULL,
                sphere TEXT NOT NULL,
                score INTEGER NOT NULL CHECK(score BETWEEN 0 AND 10),
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wheel_action_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id TEXT NOT NULL,
                sphere TEXT NOT NULL,
                action TEXT NOT NULL,
                completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS career_reflection (
                telegram_user_id TEXT PRIMARY KEY,
                interest TEXT NOT NULL,
                skill TEXT NOT NULL,
                next_experiment TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS age_access (
                telegram_user_id TEXT PRIMARY KEY,
                age_band TEXT NOT NULL DEFAULT 'unknown',
                deep_reflection_opt_in INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_state (
                telegram_user_id TEXT PRIMARY KEY,
                mode TEXT NOT NULL,
                sphere TEXT
            )
        """)
    secure_sqlite_sidecars(DB_PATH)


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
        conn.execute("INSERT INTO wheel_score_history(telegram_user_id, sphere, score) VALUES (?, ?, ?)",
                     (user_id, sphere, score))
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
    # Telegram embeds the bot token in its API URL. Never expose HTTP exception
    # messages or tracebacks: they may include the full request URL and token.
    try:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/{method}", json=payload or {}
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError("Telegram returned an unsuccessful response")
        return data["result"]
    except (httpx.HTTPError, ValueError, KeyError, RuntimeError):
        raise RuntimeError(f"Telegram API {method} failed (details redacted)") from None


async def send(client: httpx.AsyncClient, token: str, chat_id: int, text: str, keyboard: dict | None = MENU) -> None:
    parts = split_telegram_text(text)
    for index, part in enumerate(parts):
        payload: dict[str, Any] = {"chat_id": chat_id, "text": part}
        if keyboard is not None and index == len(parts) - 1:
            payload["reply_markup"] = keyboard
        await api(client, token, "sendMessage", payload)


async def handle_message(client: httpx.AsyncClient, token: str, message: dict[str, Any]) -> None:
    user = message.get("from") or {}
    chat = message.get("chat") or {}
    if not user.get("id") or not chat.get("id"):
        return
    # Private chat only: do not expose personal reflections to group members.
    if chat.get("type") != "private" or user.get("is_bot"):
        return
    user_id = str(user["id"])
    chat_id = int(chat["id"])
    raw_text = message.get("text") or ""
    if len(raw_text) > 4000:
        await send(client, token, chat_id,
                   "Сообщение слишком длинное (максимум 4000 символов). / "
                   "Message too long (maximum 4000 characters).")
        return
    text = raw_text.strip()
    if not text:
        await send(client, token, chat_id, "Пока я обрабатываю только текстовые сообщения. Голосовые заметки добавим отдельным этапом.")
        return

    # Safety takes precedence over every scripted flow, not just LLM reflection.
    crisis = classify_crisis_message(text)
    if crisis:
        GUIDED_PENDING.pop(user_id, None)
        GUIDED_SESSIONS.pop(user_id, None)
        COACHING_SESSIONS.pop(user_id, None)
        set_state(user_id, "menu")
        await send(client, token, chat_id, crisis_response(crisis), MENU)
        return

    # Crisis support and personal-data deletion bypass the anti-abuse gate.
    if text not in {"/delete_my_data", "🗑 Удалить мои данные"}:
        status, notice = check_message(DB_PATH, user_id, text)
        if status != "allow":
            await send(client, token, chat_id, notice or "Verification required.", None)
            return

    if text in {"/delete_my_data", "🗑 Удалить мои данные"}:
        GUIDED_PENDING.pop(user_id, None)
        GUIDED_SESSIONS.pop(user_id, None)
        COACHING_SESSIONS.pop(user_id, None)
        try:
            delete_telegram_user_records(DB_PATH, user_id)
        except (sqlite3.Error, RuntimeError, ValueError):
            log.error("Telegram user data deletion failed (details redacted)")
            await send(client, token, chat_id,
                       "Не удалось подтвердить удаление данных. / Could not verify data deletion.",
                       MENU)
            return
        try:
            from app.services.diagnostic_flow import clear_diagnostic
            clear_diagnostic("telegram", user_id)
        except Exception:
            log.error("Failed to clear diagnostic data (details redacted)")
            await send(client, token, chat_id,
                       "Часть данных не удалось удалить. Обратись к администратору.",
                       MENU)
            return
        await send(client, token, chat_id,
                   "Локальные оценки, предпочтения и настройки диагностики удалены. "
                   "История сообщений в Telegram и возможные данные внешнего ИИ "
                   "не удаляются этой командой.", MENU)
        return

    if text in {"/back", "◀️ Назад"}:
        GUIDED_PENDING.pop(user_id, None)
        GUIDED_SESSIONS.pop(user_id, None)
        COACHING_SESSIONS.pop(user_id, None)
        set_state(user_id, "menu")
        await send(client, token, chat_id, "Возврат в главное меню. Незавершённая сессия отменена.", MENU)
        return

    if text == "/save_guided":
        pending = GUIDED_PENDING.get(user_id)
        if pending is None:
            await send(client, token, chat_id, "Нет завершённого итога для сохранения.", MENU)
            return
        try:
            message_id = message.get("message_id")
            if type(message_id) is not int or message_id < 0:
                raise ValueError("Missing message ID")
            save_report_once(DB_PATH, user_id, pending, message_id)
        except (ValueError, RuntimeError):
            await send(client, token, chat_id,
                       "Сохранение недоступно: необходим серверный ключ шифрования.", MENU)
            return
        GUIDED_PENDING.pop(user_id, None)
        await send(client, token, chat_id,
                   "Итог сохранён в зашифрованном виде. /my_guided — открыть.", MENU)
        return
    if text == "/discard_guided":
        GUIDED_PENDING.pop(user_id, None)
        await send(client, token, chat_id, "Временный итог удалён из памяти.", MENU)
        return
    if text == "/my_guided":
        try:
            saved = read_guided_report(DB_PATH, user_id)
        except (ValueError, RuntimeError):
            await send(client, token, chat_id, "Не удалось прочитать сохранённый итог.", MENU)
            return
        await send(client, token, chat_id, saved or "Сохранённого итога пока нет.", MENU)
        return

    if text in {"/career_questions", "🧭 Исследовать профессию",
                "/skills_questions", "🛠 Рефлексия навыков"}:
        kind = ("career" if text in {"/career_questions", "🧭 Исследовать профессию"}
                else "skills")
        GUIDED_PENDING.pop(user_id, None)
        GUIDED_SESSIONS[user_id] = begin_questionnaire(kind)
        COACHING_SESSIONS.pop(user_id, None)
        q = GUIDED_SESSIONS[user_id].current
        lang = get_language(DB_PATH, user_id)
        await send(client, token, chat_id,
                   ("Опросник без диагностики. Можно пропускать вопросы: /skip. "
                    "Отмена: /cancel. Ответы временные и не передаются ИИ.\\n\\n"
                    if lang == "ru" else
                    "Exploratory questionnaire, not a diagnosis. /skip to skip; "
                    "/cancel to stop. Answers stay in temporary memory.\\n\\n")
                   + (q.en if lang == "en" else q.ru), MENU)
        return
    if text in {"/guided", "📝 Рефлексия с итогом"}:
        GUIDED_PENDING.pop(user_id, None)
        GUIDED_SESSIONS[user_id] = start_guided()
        COACHING_SESSIONS.pop(user_id, None)
        q = GUIDED_SESSIONS[user_id].current
        await send(client, token, chat_id,
                   "Рефлексия из пяти вопросов. Ответы хранятся только в памяти "
                   "до завершения или отмены и не отправляются в ИИ. "
                   "/skip — пропустить, /cancel — отменить.\\n\\n" + q.ru,
                   MENU)
        return
    if user_id in GUIDED_SESSIONS:
        if text in {"/cancel", "/back", "↩️ Главное меню", "/start", "стоп", "отмена"}:
            GUIDED_SESSIONS.pop(user_id, None)
            await send(client, token, chat_id,
                       "Рефлексия отменена, временные ответы удалены.", MENU)
            return
        try:
            session = guided_advance(GUIDED_SESSIONS[user_id],
                                     None if text == "/skip" else text)
        except ValueError:
            await send(client, token, chat_id,
                       "Ответ слишком длинный. До 1000 символов или /skip.", MENU)
            return
        if session.finished:
            GUIDED_SESSIONS.pop(user_id, None)
            locale = get_language(DB_PATH, user_id)
            report = guided_summary(session, locale)
            if session.questions[0].id == "goal":
                report += "\n\n" + build_action_plan(session, locale)
            elif session.questions[0].id == "interests":
                report += "\n\n" + career_hypotheses(session, locale)
            GUIDED_PENDING[user_id] = report
            await send(client, token, chat_id,
                       report + "\n\nСохранить итог? /save_guided — сохранить зашифрованно; "
                       "/discard_guided — не сохранять.", MENU)
        else:
            GUIDED_SESSIONS[user_id] = session
            question = session.current
            lang = get_language(DB_PATH, user_id)
            await send(client, token, chat_id,
                       f"Вопрос {len(session.responses) + 1}/{len(session.questions)}\\n\\n"
                       + (question.en if lang == "en" else question.ru)
                       + "\\n\\n/skip — пропустить, /cancel — отменить.", MENU)
        return

    # Stateless channel adapter over the explicit-consent coaching state machine.
    # Session answers remain in process memory only, not in SQLite.
    if text in {"/coaching_session", "🧭 Коучинг по шагам"}:
        COACHING_SESSIONS[user_id] = CoachingSession()
        await send(client, token, chat_id,
                   "Пошаговая коучинговая сессия. /cancel — отмена.\\n"
                   + COACHING_PROMPTS[CoachingStage.CONSENT], MENU)
        return
    if user_id in COACHING_SESSIONS:
        if text in {"/cancel", "отмена", "стоп", "↩️ Главное меню", "/start"}:
            COACHING_SESSIONS.pop(user_id, None)
            if text != "/start":
                await send(client, token, chat_id, "Сессия отменена; ответы не сохранены.", MENU)
                return
        else:
            current, prompt = coaching_advance(COACHING_SESSIONS[user_id], text)
            if current.stage in {CoachingStage.DONE, CoachingStage.CANCELLED}:
                COACHING_SESSIONS.pop(user_id, None)
            else:
                COACHING_SESSIONS[user_id] = current
            await send(client, token, chat_id, prompt, MENU)
            return

    if text in {"/menu_en", "/help_en"}:
        await send(
            client, token, chat_id,
            "Yugatneo BOT — English navigation (beta)\\n\\n"
            "/parenting — child development topics (English after /lang_en)\\n"
            "/parenting_all — all parenting topics\\n"
            "/parenting_en — simplified English parenting lessons\\n"
            "/language — change language\\n"
            "/start — welcome\\n"
            "/delete_my_data — erase locally stored user records\\n\\n"
            "The balance wheel, coaching and career guidance are not yet fully translated. "
            "This bot is for education and self-reflection, not diagnosis or therapy.",
            MENU,
        )
        return

    if text in {"/language", "/lang", "🌐 Язык / Language"}:
        await send(client, token, chat_id,
                   "Выберите язык / Choose language: /lang_ru — Русский; /lang_en — English. "
                   "English currently covers language controls and parenting education; "
                   "other coaching flows are still in Russian.", MENU)
        return

    if text in {"/lang_ru", "/lang_en"}:
        language = "en" if text == "/lang_en" else "ru"
        set_language(DB_PATH, user_id, language)
        set_state(user_id, "menu")
        await send(client, token, chat_id,
                   "English selected. English navigation: /menu_en. Parenting topics: /parenting. "
                   "Other sections are not fully translated yet."
                   if language == "en" else "Выбран русский язык.", MENU)
        return

    if text in {"/parenting_en", "/parenting_en_all"}:
        from app.services.parenting_en import TOPICS_EN
        if text == "/parenting_en_all":
            for topic in TOPICS_EN:
                await send(client, token, chat_id, topic, MENU)
        else:
            await send(client, token, chat_id,
                       "Parenting and developmental psychology topics:\n\n" +
                       "\n".join(f"{i+1}. /parenting_en_{i+1}" for i in range(len(TOPICS_EN))),
                       MENU)
        return

    if text.startswith("/parenting_en_"):
        from app.services.parenting_en import TOPICS_EN
        try:
            number = int(text.removeprefix("/parenting_en_"))
            if not 1 <= number <= len(TOPICS_EN):
                raise ValueError()
        except ValueError:
            await send(client, token, chat_id, "Unknown topic. Use /parenting_en.", MENU)
        else:
            await send(client, token, chat_id, TOPICS_EN[number - 1], MENU)
        return

    if text.lower() in CANCEL_WORDS:
        set_state(user_id, "menu")
        await send(client, token, chat_id, "Остановил текущий сценарий. Выбирай, что делать дальше.", MENU)
        return

    if text.startswith("/start"):
        set_state(user_id, "menu")
        if get_language(DB_PATH, user_id) == "en":
            await send(client, token, chat_id,
                       "Welcome to Yugatn Neo Symbiot. Choose a self-reflection or learning activity. "
                       "You can skip any question. This bot does not diagnose or replace a professional. "
                       "For English parenting resources, use /parenting. "
                       "Some other activities are still available in Russian. "
                       "Switch language with /language.", MENU)
            return
        await send(
            client, token, chat_id,
            "Привет! Я Yugatn Neo Symbiot — помощник для коучинга, самоисследования и психообразования.\n\n"
            "Можно пропустить любой вопрос или остановиться. Я не ставлю диагнозы и не заменяю специалиста. "
            "Не отправляй пароли и данные, которые не хочешь передавать сервису.\n\n"
            "Выбери «Колесо баланса» для субъективной оценки сфер жизни от 0 до 10 или «Рефлексия» для диалога. «Вопросы» и «Диалог по ответам» работают без ИИ.",
            MENU,
        )
        return

    if text in SUBMENUS:
        GUIDED_PENDING.pop(user_id, None)
        GUIDED_SESSIONS.pop(user_id, None)
        COACHING_SESSIONS.pop(user_id, None)
        set_state(user_id, "menu")
        await send(client, token, chat_id, "Выбери действие или вернись в главное меню.",
                   submenu_keyboard(text))
        return

    if text == "🗑 Удалить мои данные":
        text = "/delete_my_data"

    if text == "❔ Помощь" or text == "/help":
        await send(client, token, chat_id, "Команды: /start — меню; /language — язык; /parenting_en — English parenting; /parenting — цифровая среда и родительство; /age — возрастная настройка; /career — рефлексия навыков; /report — персональная сводка; /approaches — выбрать психологический подход; /next_step — выбрать действие; /done — отметить выполнение; /wheel_history — история оценок; /questions — библиотека вопросов; /skip — пропустить вопрос; /cancel — остановить сценарий; /delete_my_data — удалить локальные данные. Оценки колеса субъективны и не являются диагностикой.", MENU)
        return

    if text in {"/wheel_rays", "🌈 Выбрать луч"}:
        rays = catalog(True)
        await send(client, token, chat_id,
                   "Доступные направления и их составляющие:\\n"
                   + "\\n".join("• " + ray.title + ": " + ", ".join(ray.facets) for ray in rays)
                   + "\\n\\nЧтобы оценить направление, используй /wheel. "
                     "Можно ввести собственное название.", MENU)
        return

    if text in {"🧭 Колесо баланса", "/wheel"}:
        set_state(user_id, "wheel_name")
        await send(client, token, chat_id, tr(get_language(DB_PATH, user_id), "wheel_intro"), MENU)
        return

    # Educational content stays inside Telegram; external publication is disabled.
    if text in {"/articles", "/telegraph"}:
        lang = get_language(DB_PATH, user_id)
        intro = ("Educational topics (read in Telegram):" if lang == "en"
                 else "Образовательные темы (чтение в Telegram):")
        await send(client, token, chat_id,
                   intro + "\n" + "\n".join(
                       f"• /parenting {topic.key}" for topic in TOPICS
                   ), MENU)
        return

    if text.startswith("/article "):
        key = text.partition(" ")[2].strip().lower()
        topic = next((item for item in TOPICS if item.key == key), None)
        if topic is None:
            await send(client, token, chat_id,
                       "Unknown topic / Неизвестная тема. /articles", MENU)
            return
        lang = get_language(DB_PATH, user_id)
        await send(client, token, chat_id,
                   english_topic(topic.key) if lang == "en"
                   else format_topic(topic), MENU)
        return

    if text in {"/knowledge_parenting", "📖 Источники по воспитанию"}:
        lang = get_language(DB_PATH, user_id)
        delivery = source_bounded_answer("parenting", locale=lang)
        await send(client, token, chat_id, delivery.text, MENU)
        return

    if text in {"👨‍👩‍👧 Родительство", "/parenting"}:
        lang = get_language(DB_PATH, user_id)
        options = "\n".join(f"• {topic.key} — {english_topic(topic.key).split(chr(10))[0] if lang == 'en' else topic.title}" for topic in TOPICS)
        intro = ("📚 Parenting and child development. Choose /parenting TOPIC or /parenting_all.\n\n" if lang == "en" else "📚 Возрастная психология и родительство. Выбери /parenting ТЕМА или /parenting_all.\n\n")
        await send(client, token, chat_id, intro + options, MENU)
        return

    if text == "/parenting_all":
        lang = get_language(DB_PATH, user_id)
        for topic in TOPICS:
            await send(client, token, chat_id,
                       english_topic(topic.key) if lang == "en" else format_topic(topic), MENU)
        return

    if text.startswith("/parenting "):
        query = text.partition(" ")[2].strip()
        init_index(DB_PATH)
        topics = search_index(DB_PATH, query, limit=3)
        if not topics:
            await send(client, token, chat_id,
                       "Тема не найдена. Напиши /parenting для списка.", MENU)
        else:
            await send(client, token, chat_id,
                       "\n\n".join(english_topic(topic.key) if get_language(DB_PATH, user_id) == "en"
                                     else format_topic(topic) for topic in topics[:3]), MENU)
        return

    if text in {"🎓 Навыки и профессии", "/career", "/career_en"}:
        set_state(user_id, "career_interest")
        await send(client, token, chat_id, tr(get_language(DB_PATH, user_id), "career_intro"), MENU)
        return

    if text in {"📄 Мой отчёт", "/report"}:
        scores = get_scores(user_id)
        with sqlite3.connect(DB_PATH) as conn:
            active = conn.execute(
                "SELECT sphere, action FROM wheel_actions WHERE telegram_user_id=?",
                (user_id,)).fetchone()
            completed = conn.execute(
                "SELECT sphere, action, completed_at FROM wheel_action_history "
                "WHERE telegram_user_id=? ORDER BY id DESC LIMIT 5",
                (user_id,)).fetchall()
        with sqlite3.connect(DB_PATH) as conn:
            career = conn.execute(
                "SELECT interest, skill, next_experiment FROM career_reflection "
                "WHERE telegram_user_id=?", (user_id,)).fetchone()
        if active is not None:
            active = (active[0], decrypt_diagnostic_json(active[1]))
        completed = [(sphere, decrypt_diagnostic_json(action), date)
                     for sphere, action, date in completed]
        if career is not None:
            career = tuple(decrypt_diagnostic_json(value) for value in career)
        report = build_report(get_language(DB_PATH, user_id), scores, career, active, completed)
        await send(client, token, chat_id, report, MENU)
        return

    if text in {"📈 История колеса", "/wheel_history"}:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT sphere, score, recorded_at FROM wheel_score_history "
                "WHERE telegram_user_id=? ORDER BY id DESC LIMIT 15", (user_id,)
            ).fetchall()
        if not rows:
            await send(client, token, chat_id, "История пока пуста. Начни с колеса баланса.", MENU)
        else:
            lines = ["Последние 15 оценок (от новых к старым):"]
            lines.extend(f"• {date}: {sphere} — {score}/10" for sphere, score, date in rows)
            await send(client, token, chat_id, "\n".join(lines), MENU)
        return

    if text in {"✅ Отметить выполнение", "/done"}:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("SELECT sphere, action FROM wheel_actions WHERE telegram_user_id=?",
                               (user_id,)).fetchone()
            if row:
                conn.execute(
                    "INSERT INTO wheel_action_history(telegram_user_id, sphere, action) VALUES (?, ?, ?)",
                    (user_id, row[0], row[1]))
                conn.execute("DELETE FROM wheel_actions WHERE telegram_user_id=?", (user_id,))
        if row:
            row = (row[0], decrypt_diagnostic_json(row[1]))
            await send(client, token, chat_id,
                       f"Отмечено выполненным: {row[0]} — {row[1]}. "
                       "Если хочешь, оцени сферу заново и сравни с прошлой оценкой.", MENU)
        else:
            await send(client, token, chat_id,
                       "Нет выбранного шага. Выбери его через «🎯 Следующий шаг».", MENU)
        return

    if text in {"🎯 Следующий шаг", "/next_step"}:
        scores = get_scores(user_id)
        if not scores:
            await send(client, token, chat_id, "Сначала добавь хотя бы одну оценку в колесе баланса.", MENU)
            return
        options_text = "\n".join(f"• {name}: {score}/10" for name, score in scores)
        set_state(user_id, "wheel_action_sphere")
        await send(client, token, chat_id,
                   "Выбери одну сферу, в которой хочешь сделать небольшой шаг. "
                   "Напиши её название точно как в списке:\n" + options_text +
                   "\n\nМожно выбрать любую сферу, не обязательно с минимальной оценкой.", MENU)
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

    if text in {"/age", "🛡 Возрастные настройки"}:
        set_state(user_id, "age_select")
        await send(client, token, chat_id,
                   "Выбери возрастную группу: до 18, 18–26 или 27+. "
                   "Можно отказаться; тогда останется базовый режим. "
                   "Это самоописание, а не проверка документов.",
                   {"keyboard": [[{"text": "До 18"}, {"text": "18–26"}, {"text": "27+"}],
                                 [{"text": "↩️ Главное меню"}]], "resize_keyboard": True})
        return

    if text in {"🧠 Выбрать подход", "/approaches"}:
        set_state(user_id, "approach_select")
        keyboard = {"keyboard": [[{"text": name}] for name in APPROACHES]
                    + [[{"text": "↩️ Главное меню"}]], "resize_keyboard": True}
        await send(client, token, chat_id,
                   "Выбери подход для самостоятельной психологической рефлексии. "
                   "Это образовательные упражнения, не психотерапия и не диагностика. "
                   "Любой вопрос можно пропустить.", keyboard)
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
                   + "\n\nВыбери только те настройки, которые хочешь сообщить. "
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

    if text == "🤖 Продолжить с ИИ":
        if mode.startswith("branch:"):
            node_id = mode.split(":", 1)[1]
            if node_id in NODES and not options(node_id):
                if read_prefs(user_id).age_group == "under_18":
                    await send(client, token, chat_id,
                               "Для несовершеннолетних переход к ИИ из этого сценария "
                               "пока отключён. Можно пользоваться бесплатными вопросами.",
                               terminal_keyboard())
                    return
                set_state(user_id, "ai_branch", node_id)
                await send(client, token, chat_id,
                           "Ты выбрал продолжение с ИИ. Следующее сообщение будет "
                           "отправлено подключённому ИИ-провайдеру, если он настроен. "
                           "Передаётся текст твоего сообщения и краткая тема ветки. "
                           "Не отправляй медицинские документы и другие чувствительные данные. "
                           "Для отказа — /cancel. Напиши, что хочешь обсудить.", MENU)
                return
        await send(client, token, chat_id,
                   "Сначала выбери тему через «🌿 Диалог по ответам».", MENU)
        return

    if mode == "ai_branch":
        node_id = sphere or ""
        incoming = IncomingMessage(
            channel=Channel.TELEGRAM, external_user_id=user_id,
            text=text, message_id=str(message.get("message_id", "")) or None)
        try:
            reply = await respond(incoming, conversation_summary=(
                question_context(node_id) if node_id in NODES else ""))
            await send(client, token, chat_id, reply.text, MENU)
        except Exception:
            log.exception("AI handoff unavailable")
            await send(client, token, chat_id,
                       "ИИ сейчас недоступен. Бесплатные вопросы продолжают работать.", MENU)
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
            await send(client, token, chat_id,
                       branch_prompt(next_id) + (branch_catalog_suggestion(next_id, read_prefs(user_id))
                       if not options(next_id) else ""),
                       branch_keyboard(next_id) if options(next_id) else terminal_keyboard())
        elif options(node_id):
            await send(client, token, chat_id,
                       "Выбери вариант кнопкой. Если ни один не подходит, "
                       "можно выйти и воспользоваться свободной рефлексией.",
                       branch_keyboard(node_id))
        else:
            await send(client, token, chat_id,
                       "Спасибо за ответ. Это вопрос для самостоятельного "
                       "осмысления, а не оценка личности. Можно перейти к "
                       "свободной рефлексии через главное меню.", terminal_keyboard())
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

    if mode == "age_select":
        if text not in {"До 18", "18–26", "27+"}:
            await send(client, token, chat_id, "Выбери возрастную группу из списка или /cancel.", MENU)
            return
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO age_access(telegram_user_id, age_band, deep_reflection_opt_in) "
                "VALUES (?, ?, 0) ON CONFLICT(telegram_user_id) DO UPDATE SET "
                "age_band=excluded.age_band, deep_reflection_opt_in=0", (user_id, text))
        set_state(user_id, "menu")
        await send(client, token, chat_id,
                   "Возрастная настройка сохранена. Базовые упражнения доступны всем. "
                   "Глубокие экспериментальные сценарии пока не активированы.", MENU)
        return

    if mode == "parenting":
        set_state(user_id, "menu")
        await send(client, token, chat_id,
                   "Спасибо за размышление. Можно начать с одного выбранного момента "
                   "без отвлечений на смартфон. Это добровольный эксперимент, а не оценка "
                   "твоих родительских качеств. Ответ не сохраняется.", MENU)
        return

    if mode == "career_interest":
        if len(text) > 300:
            await send(client, token, chat_id, tr(get_language(DB_PATH, user_id), "too_long"), MENU)
            return
        set_state(user_id, "career_skill", text)
        await send(client, token, chat_id, tr(get_language(DB_PATH, user_id), "career_skill"), MENU)
        return

    if mode == "career_skill":
        if len(text) > 300:
            await send(client, token, chat_id, "Пожалуйста, сократи ответ до 300 символов.", MENU)
            return
        set_state(user_id, "career_experiment")
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO career_reflection(telegram_user_id, interest, skill, next_experiment) "
                         "VALUES (?, ?, ?, '') ON CONFLICT(telegram_user_id) DO UPDATE SET "
                         "interest=excluded.interest, skill=excluded.skill, next_experiment=''",
                         (user_id, encrypt_diagnostic_json(sphere or ""), encrypt_diagnostic_json(text)))
        await send(client, token, chat_id, tr(get_language(DB_PATH, user_id), "career_experiment"), MENU)
        return

    if mode == "career_experiment":
        if len(text) > 300:
            await send(client, token, chat_id, "Пожалуйста, сократи ответ до 300 символов.", MENU)
            return
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE career_reflection SET next_experiment=?, updated_at=CURRENT_TIMESTAMP "
                         "WHERE telegram_user_id=?", (encrypt_diagnostic_json(text), user_id))
        set_state(user_id, "menu")
        await send(client, token, chat_id, tr(get_language(DB_PATH, user_id), "career_saved"), MENU)
        return

    if mode == "approach_select":
        if text not in APPROACHES:
            await send(client, token, chat_id,
                       "Выбери название подхода из предложенного списка или /cancel.")
            return
        set_state(user_id, "approach_practice", text)
        await send(client, token, chat_id,
                   f"Направление: {text}.\n\n{APPROACHES[text]}\n\n"
                   "Это упражнение для самоисследования. /cancel — завершить.", MENU)
        return

    if mode == "approach_practice":
        await send(client, token, chat_id,
                   "Спасибо за размышление. Можешь продолжить самостоятельно, "
                   "выбрать другой подход через «🧠 Выбрать подход» или завершить /cancel. "
                   "Ответы этого упражнения не сохраняются.", MENU)
        return

    if mode == "wheel_action_sphere":
        matches = [name for name, _ in get_scores(user_id) if name.casefold() == text.casefold()]
        if not matches:
            await send(client, token, chat_id, "Такой сферы в твоих оценках нет. Введи название из списка или /cancel.", MENU)
            return
        set_state(user_id, "wheel_action_text", matches[0])
        await send(client, token, chat_id,
                   f"Какое одно небольшое, выполнимое действие для сферы «{matches[0]}» ты готов выбрать? "
                   "Напиши конкретный шаг своими словами (до 300 символов).", MENU)
        return

    if mode == "wheel_action_text":
        action = re.sub(r"\\s+", " ", text).strip()
        if not action or len(action) > 300:
            await send(client, token, chat_id, "Опиши один шаг длиной от 1 до 300 символов или /cancel.", MENU)
            return
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO wheel_actions(telegram_user_id, sphere, action) VALUES (?, ?, ?) "
                         "ON CONFLICT(telegram_user_id) DO UPDATE SET sphere=excluded.sphere, "
                         "action=excluded.action, updated_at=CURRENT_TIMESTAMP", (user_id, sphere, encrypt_diagnostic_json(action)))
        set_state(user_id, "menu")
        await send(client, token, chat_id,
                   f"Твой выбранный шаг для «{sphere}»: {action}\n\n"
                   "Это твоё решение, а не предписание. При необходимости можешь изменить его через «🎯 Следующий шаг».", MENU)
        return

    if mode == "wheel_name":
        try:
            sphere = normalize_ray_title(text)
        except ValueError:
            await send(client, token, chat_id,
                       "Название луча должно содержать от 1 до 80 символов.", MENU)
            return
        set_state(user_id, "wheel_score", sphere)
        await send(client, token, chat_id, tr(get_language(DB_PATH, user_id), "wheel_score_prompt", sphere=sphere))
        return

    if mode == "wheel_score":
        if not re.fullmatch(r"(10|[0-9])", text):
            await send(client, token, chat_id, tr(get_language(DB_PATH, user_id), "wheel_invalid"), None)
            return
        score = int(text)
        save_score(user_id, sphere or "Без названия", score)
        set_state(user_id, "wheel_name")
        await send(client, token, chat_id, tr(get_language(DB_PATH, user_id), "wheel_saved", sphere=sphere, score=score), MENU)
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
            log.error("Reflection response failed (details redacted)")
            await send(client, token, chat_id, "Не удалось подготовить ответ. Попробуй ещё раз чуть позже.", MENU)
        return

    set_state(user_id, "menu")
    await send(client, token, chat_id, "Выбери действие в меню. Если хочешь начать заново, отправь /start.", MENU)


from app.services.async_update_dispatch import dispatch_update
from app.services.update_quarantine import quarantine_if_exhausted
from app.services.update_jobs import status as update_job_status


async def main() -> None:
    validate_encryption_startup()
    settings = get_settings()
    token = settings.telegram_bot_token
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN не задан. Добавь токен в локальный .env; не публикуй его в GitHub или чате.")
    init_db()
    offset: int | None = None
    timeout = httpx.Timeout(40.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        me = await api(client, token, "getMe")
        webhook = await api(client, token, "getWebhookInfo")
        if webhook.get("url"):
            raise SystemExit(
                "Telegram webhook is active. Polling cannot run simultaneously. "
                "Disable the webhook explicitly in your deployment configuration; "
                "this program will not delete it automatically."
            )
        log.info("Polling started for @%s. Stop with Ctrl+C.", me.get("username", "bot"))
        while True:
            params: dict[str, Any] = {"timeout": 30, "allowed_updates": ["message"]}
            if offset is not None:
                params["offset"] = offset
            try:
                updates = await api(client, token, "getUpdates", params)
                for update in updates:
                    update_id = update["update_id"]
                    try:
                        if update.get("message"):
                            processed = await dispatch_update(
                                DB_PATH, update_id,
                                lambda: handle_message(client, token, update["message"]),
                            )
                            if not processed:
                                job = update_job_status(DB_PATH, update_id)
                                if job and job[0] == 'quarantined':
                                    raise SystemExit('Telegram update quarantined; operator review required')
                                if job and job[0] == 'done':
                                    # Completed before the previous polling offset was acknowledged.
                                    offset = update_id + 1
                                    continue
                                # An earlier attempt still holds its lease.
                                # Do not acknowledge this or later updates.
                                await asyncio.sleep(3)
                                break
                        offset = update_id + 1
                    except Exception:
                        # Do not advance offset after a failed handler.
                        # Telegram will redeliver after the processing lease.
                        if quarantine_if_exhausted(DB_PATH, update_id):
                            log.error("Telegram update quarantined after repeated failures (redacted)")
                            raise SystemExit("Telegram update quarantined; operator review required")
                        log.error("Telegram update failed; awaiting safe retry (redacted)")
                        await asyncio.sleep(3)
                        break
            except (httpx.HTTPError, RuntimeError):
                log.error("Telegram polling error; retrying in 3 seconds (details redacted)")
                await asyncio.sleep(3)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot stopped by user.")
