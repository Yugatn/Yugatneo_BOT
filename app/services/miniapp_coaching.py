"""Ephemeral, strictly owner-scoped Wheel coaching state (staging only).

Answers are validated and immediately discarded. No raw transcript, no model
calls, and no persisted sensitive records. Single-process memory is intentional:
multi-worker / multi-instance deployments require a reviewed shared store.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from threading import RLock
from time import monotonic
from typing import Callable
import re
import secrets

from app.services.safety import classify_crisis_message, crisis_response


PROMPTS: dict[str, tuple[str, ...]] = {
    "reflection": (
        "Какие наблюдения или события связаны для вас с этой оценкой? Можно не раскрывать личные подробности.",
        "Что в этой ситуации вы знаете точно, а что остаётся неизвестным?",
        "Какие чувства и потребности вы замечаете? Можно пропустить вопрос.",
        "Что уже помогает вам справляться или сохранять важное?",
        "Какое понимание вы хотели бы сохранить из этого размышления?",
    ),
    "reframe": (
        "Опишите обстоятельства, связанные с выбранной оценкой. Что произошло в действительности?",
        "Какую мысль или интерпретацию вы связываете с этой ситуацией?",
        "Что подтверждает эту мысль, а что могло бы ей противоречить?",
        "Какая ещё интерпретация возможна, не отрицая реальных трудностей? Можно сохранить исходный взгляд.",
        "Как можно безопасно проверить альтернативу? Ничего менять тоже допустимо.",
    ),
    "coaching": (
        "Что вы сами хотите изменить или сохранить в этой сфере? Отсутствие изменений — тоже выбор.",
        "Какую ситуацию вы наблюдаете сейчас и что пока лишь предполагаете?",
        "Какие ресурсы уже доступны и чего, возможно, не хватает?",
        "Какие два возможных действия вы видите, включая возможность не предпринимать ничего?",
        "Какой один небольшой и безопасный шаг вы хотели бы выбрать?",
        "Когда и по какому наблюдаемому признаку вы сами решите оценить результат?",
    ),
}

# The pilot excludes topics that require separate clinical/privacy review.
# Only these non-clinical, public catalogue coordinates are accepted remotely.
# Health and sensitive thematic wheels remain offline pending expert review.
PILOT_RAY_COUNTS: dict[str, int] = {
    "main": 9, "work": 8, "finance": 8, "relationships": 8,
    "social": 8, "development": 8, "rest": 8, "creativity": 8,
    "self_awareness": 8,
}
PILOT_WHEELS = frozenset(PILOT_RAY_COUNTS)
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{32}$")


class UnknownSession(LookupError):
    """No such active, unexpired session owned by this authenticated subject."""


class StaleTurn(ValueError):
    """Client tried to replay or skip a dialogue step."""


class SessionCapacity(ValueError):
    """Session limit reached. Avoid unbounded user data in server memory."""


@dataclass(frozen=True, slots=True)
class State:
    owner: str
    mode: str
    step: int
    expires_at: float


@dataclass(frozen=True, slots=True)
class Outcome:
    finished: bool
    step: int | None
    question: str | None
    handoff: str | None = None
    safety: str | None = None


class SessionRegistry:
    def __init__(
        self,
        *,
        clock: Callable[[], float] = monotonic,
        ttl_seconds: int = 1200,
        max_sessions: int = 256,
        max_per_user: int = 2,
    ):
        if ttl_seconds < 30 or max_sessions < 1 or max_per_user < 1:
            raise ValueError("invalid session limits")
        self._clock = clock
        self._ttl = ttl_seconds
        self._max = max_sessions
        self._per_user = max_per_user
        self._lock = RLock()
        self._entries: dict[str, State] = {}

    def _prune(self):
        now = self._clock()
        for key, record in list(self._entries.items()):
            if record.expires_at <= now:
                del self._entries[key]

    def _owned(self, user_id: str, session_id: str) -> State:
        self._prune()
        if not user_id or not SESSION_ID_RE.fullmatch(session_id):
            raise UnknownSession()
        record = self._entries.get(session_id)
        if record is None or not secrets.compare_digest(record.owner, user_id):
            raise UnknownSession()
        return record

    def start(self, user_id: str, mode: str) -> tuple[str, State]:
        if not user_id or mode not in PROMPTS:
            raise ValueError("invalid owner or coaching mode")
        with self._lock:
            self._prune()
            if len(self._entries) >= self._max:
                raise SessionCapacity("server session limit reached")
            if sum(s.owner == user_id for s in self._entries.values()) >= self._per_user:
                raise SessionCapacity("subject session limit reached")
            token = secrets.token_urlsafe(24)
            while token in self._entries:
                token = secrets.token_urlsafe(24)
            record = State(owner=user_id, mode=mode, step=0,
                           expires_at=self._clock() + self._ttl)
            self._entries[token] = record
            return token, record

    def status(self, user_id: str, session_id: str) -> State:
        with self._lock:
            return self._owned(user_id, session_id)

    def advance(
        self,
        user_id: str,
        session_id: str,
        *,
        expected_step: int,
        action: str,
        text: str | None = None,
    ) -> Outcome:
        """Atomically advance; never save or return raw user text."""
        with self._lock:
            current = self._owned(user_id, session_id)
            if expected_step != current.step:
                raise StaleTurn("stale or repeated step")
            if action == "stop":
                if text:
                    raise ValueError("stop cannot include an answer")
                del self._entries[session_id]
                return Outcome(True, None, None)
            if action == "skip":
                if text:
                    raise ValueError("skip cannot include an answer")
            elif action == "answer":
                if not isinstance(text, str) or not 1 <= len(text.strip()) <= 2000:
                    raise ValueError("answer must be 1..2000 characters")
                level = classify_crisis_message(text)
                if level is not None:
                    del self._entries[session_id]
                    return Outcome(True, None, None, crisis_response(level), level)
            else:
                raise ValueError("unsupported action")
            next_step = current.step + 1
            if next_step >= len(PROMPTS[current.mode]):
                del self._entries[session_id]
                return Outcome(True, None, None)
            self._entries[session_id] = replace(current, step=next_step)
            return Outcome(False, next_step, PROMPTS[current.mode][next_step])

    def erase(self, user_id: str, session_id: str) -> None:
        with self._lock:
            self._owned(user_id, session_id)
            del self._entries[session_id]

    def erase_all(self, user_id: str) -> int:
        if not user_id:
            raise ValueError("authenticated owner required")
        with self._lock:
            self._prune()
            keys = [key for key, record in self._entries.items()
                    if secrets.compare_digest(record.owner, user_id)]
            for key in keys:
                del self._entries[key]
            return len(keys)
