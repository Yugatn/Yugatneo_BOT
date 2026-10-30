"""Disabled-by-default Telegram Mini App coaching API (non-clinical staging).

Every operation verifies Telegram initData again. No client-supplied user IDs,
persistent chat transcript, LLM/model calls, or unrestricted web CORS.
"""
from __future__ import annotations

from typing import Literal
from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import get_settings
from app.miniapp_wheel_api import identity
from app.services.miniapp_coaching import (
    PROMPTS, PILOT_WHEELS, SessionRegistry,
    SessionCapacity, StaleTurn, UnknownSession,
)
from app.services.security import allow_request


router = APIRouter(prefix="/api/v1/miniapp/coaching", tags=["miniapp-coaching"])
sessions = SessionRegistry()
PRIVACY_NOTICE = (
    "Сценарий не является психотерапией или диагностикой. "
    "Сервер обрабатывает выбранный контекст и каждый отдельный ответ, "
    "но не сохраняет текст ответов, не передаёт их языковой модели "
    "и не синхронизирует с Колесом баланса. "
    "Сессия находится только в памяти одного серверного процесса не более 20 минут."
)


class StartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    wheel_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    ray_id: str = Field(min_length=1, max_length=100)
    score: int | None = Field(default=None, ge=0, le=10, strict=True)
    mode: Literal["reflection", "reframe", "coaching"]
    consent_for_server_processing: bool = Field(strict=True)
    adult_attested: bool = Field(strict=True)


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_step: int = Field(ge=0, le=10, strict=True)
    action: Literal["answer", "skip", "stop"]
    text: str | None = Field(default=None, max_length=2000)


def authorized_subject(authorization: str | None) -> str:
    settings = get_settings()
    # Second, independent gate: toggling a staging feature flag cannot
    # accidentally make this unreviewed psychology feature public.
    if settings.app_env.lower() in {"production", "prod"}:
        raise HTTPException(503, "Coaching API has not passed production review")
    if not settings.miniapp_coaching_enabled:
        raise HTTPException(503, "Coaching API is disabled")
    return identity(authorization)


def limited(user_id: str):
    if not allow_request(f"miniapp-coach:{user_id}", limit=30, window_seconds=60):
        raise HTTPException(429, "Too many coaching requests")


def view(state, session_id: str) -> dict:
    return {
        "session_id": session_id,
        "mode": state.mode,
        "step": state.step,
        "question": PROMPTS[state.mode][state.step],
        "total_steps": len(PROMPTS[state.mode]),
        "transcript_persisted": False,
    }


@router.post("/sessions", status_code=201)
def start(
    body: StartRequest,
    authorization: str | None = Header(default=None),
):
    owner = authorized_subject(authorization)
    limited(owner)
    if not body.consent_for_server_processing:
        raise HTTPException(403, "Explicit server-processing consent required")
    if not body.adult_attested:
        raise HTTPException(403, "Adult pilot only (self-attestation is not age verification)")
    if body.wheel_id not in PILOT_WHEELS:
        raise HTTPException(422, "This wheel is not included in the supervised pilot")
    try:
        session_id, record = sessions.start(owner, body.mode)
    except SessionCapacity:
        raise HTTPException(429, "Coaching session capacity reached") from None
    return {**view(record, session_id), "privacy_notice": PRIVACY_NOTICE}


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    authorization: str | None = Header(default=None),
):
    owner = authorized_subject(authorization)
    try:
        return view(sessions.status(owner, session_id), session_id)
    except UnknownSession:
        raise HTTPException(404, "Session not found") from None


@router.post("/sessions/{session_id}/turns")
def turn(
    session_id: str,
    body: TurnRequest,
    authorization: str | None = Header(default=None),
):
    owner = authorized_subject(authorization)
    limited(owner)
    try:
        result = sessions.advance(
            owner, session_id,
            expected_step=body.expected_step,
            action=body.action,
            text=body.text,
        )
    except UnknownSession:
        raise HTTPException(404, "Session not found") from None
    except StaleTurn:
        raise HTTPException(409, "Step conflict; refresh the session state") from None
    except ValueError:
        # Do not echo any client text in errors.
        raise HTTPException(422, "Invalid coaching action or answer") from None
    return {
        "finished": result.finished,
        "step": result.step,
        "question": result.question,
        "handoff": result.handoff,
        "safety": result.safety,
        "transcript_persisted": False,
    }


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    authorization: str | None = Header(default=None),
):
    owner = authorized_subject(authorization)
    try:
        sessions.erase(owner, session_id)
    except UnknownSession:
        raise HTTPException(404, "Session not found") from None
    return Response(status_code=204)


@router.delete("/sessions", status_code=204)
def delete_all_sessions(authorization: str | None = Header(default=None)):
    owner = authorized_subject(authorization)
    sessions.erase_all(owner)
    return Response(status_code=204)
