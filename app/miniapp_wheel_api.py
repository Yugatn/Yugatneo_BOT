"""Authenticated Mini App wheel API.

Mount via app.include_router(router). Browser sends Telegram initData in
Authorization: tma <initData>. The server never accepts client-supplied user IDs.
"""
import sqlite3
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.telegram_miniapp_auth import verify_init_data, InvalidInitData
from app.services.wheel_domain import RayScore
from app.services.wheel_snapshot_store import save, history

router = APIRouter(prefix="/api/v1/miniapp/wheel", tags=["miniapp-wheel"])
DB = Path(__file__).resolve().parents[2] / "yugatneo_bot.sqlite3"


class Answer(BaseModel):
    ray_id: str = Field(min_length=1, max_length=80)
    score: int = Field(ge=0, le=10)


class Assessment(BaseModel):
    wheel_version: int = Field(default=1, ge=1)
    answers: list[Answer] = Field(min_length=1, max_length=60)


def identity(authorization: str | None) -> str:
    token = get_settings().telegram_bot_token
    if not token:
        raise HTTPException(503, "Telegram Mini App is not configured")
    if not authorization or not authorization.startswith("tma "):
        raise HTTPException(401, "Telegram initData required")
    try:
        return verify_init_data(authorization[4:], token)["user_id"]
    except InvalidInitData:
        raise HTTPException(401, "Invalid or expired Telegram session") from None


@router.get("/history")
def get_history(authorization: str | None = Header(default=None), limit: int = 30):
    user_id = identity(authorization)
    if not 1 <= limit <= 100:
        raise HTTPException(422, "Invalid limit")
    with sqlite3.connect(DB) as conn:
        return {"items": history(conn, user_id, limit)}


@router.post("/assessments", status_code=201)
def create_assessment(body: Assessment, authorization: str | None = Header(default=None)):
    user_id = identity(authorization)
    try:
        scores = [RayScore(a.ray_id, a.score) for a in body.answers]
        with sqlite3.connect(DB) as conn:
            snapshot_id = save(conn, user_id, scores, body.wheel_version)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"id": snapshot_id, "saved": True}
