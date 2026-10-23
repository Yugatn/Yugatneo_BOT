"""Low-friction anti-abuse gate for a Telegram polling bot.

A small arithmetic challenge is a friction measure, not proof of humanity.
Use with per-user rate limiting and infrastructure-level protections.
"""
from __future__ import annotations

import secrets
import sqlite3
import time

WINDOW_SECONDS = 60
MAX_MESSAGES = 20
CHALLENGE_TTL = 600
MAX_ATTEMPTS = 3


def init_security(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bot_security (
            telegram_user_id TEXT PRIMARY KEY,
            window_start INTEGER NOT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            verified INTEGER NOT NULL DEFAULT 0,
            challenge_answer TEXT,
            challenge_expires INTEGER,
            attempts INTEGER NOT NULL DEFAULT 0
        )
    """)


def check_message(db_path: str, user_id: str, text: str, now: int | None = None) -> tuple[str, str | None]:
    """Return ('allow'|'challenge'|'solved'|'limited', optional prompt)."""
    timestamp = int(time.time()) if now is None else now
    with sqlite3.connect(db_path, timeout=5) as conn:
        init_security(conn)
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT window_start, message_count, verified, challenge_answer, "
            "challenge_expires, attempts FROM bot_security WHERE telegram_user_id=?",
            (user_id,),
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO bot_security(telegram_user_id,window_start,message_count) VALUES(?,?,0)",
                (user_id, timestamp),
            )
            row = (timestamp, 0, 0, None, None, 0)
        start, count, verified, answer, expires, attempts = row
        if timestamp - start >= WINDOW_SECONDS:
            start, count = timestamp, 0
        count += 1
        conn.execute(
            "UPDATE bot_security SET window_start=?,message_count=? WHERE telegram_user_id=?",
            (start, count, user_id),
        )
        if count > MAX_MESSAGES:
            return "limited", "Слишком много сообщений. Попробуйте через минуту. / Too many messages; try again in a minute."
        if verified:
            return "allow", None
        if answer is not None and expires is not None and timestamp < expires:
            if text.strip() == "/start":
                return "challenge", "Решите пример выше или отправьте число. / Please solve the question above."
            if text.strip() == answer:
                conn.execute(
                    "UPDATE bot_security SET verified=1,challenge_answer=NULL,"
                    "challenge_expires=NULL,attempts=0 WHERE telegram_user_id=?",
                    (user_id,),
                )
                return "solved", "Проверка пройдена! / Verification complete. Send /start."
            attempts += 1
            if attempts >= MAX_ATTEMPTS:
                conn.execute(
                    "UPDATE bot_security SET challenge_answer=NULL,challenge_expires=NULL,"
                    "attempts=0 WHERE telegram_user_id=?", (user_id,)
                )
                return "challenge", "Попробуем другой пример. Отправьте /start. / Try a new question: send /start."
            conn.execute(
                "UPDATE bot_security SET attempts=? WHERE telegram_user_id=?", (attempts, user_id)
            )
            return "challenge", f"Введите ответ на пример цифрами. Осталось попыток: {MAX_ATTEMPTS - attempts}. / Enter the number."
        a = secrets.randbelow(5) + 1
        b = secrets.randbelow(5) + 1
        conn.execute(
            "UPDATE bot_security SET challenge_answer=?,challenge_expires=?,attempts=0 "
            "WHERE telegram_user_id=?", (str(a + b), timestamp + CHALLENGE_TTL, user_id),
        )
        return "challenge", f"🛡 Простая проверка / Quick check: {a} + {b} = ?\nОтправьте только число. / Reply with the number."
