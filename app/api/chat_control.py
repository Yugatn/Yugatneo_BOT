"""Private API for connecting a configured ChatGPT Action to the personal coaching bot.

This API is intentionally owner-scoped: callers with the API key can access the
single owner's wheel/goals. Never expose the key in a browser, Telegram message,
repository, or client-side app. Use HTTPS in deployment.
"""
from __future__ import annotations

import hmac
import os
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.models import Channel, IncomingMessage
from app.services.dialogue import respond

router = APIRouter(prefix="/api/v1", tags=["private-chat-control"])
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "yugatneo_bot.sqlite3"


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    expected = get_settings().chat_control_api_key
    if not expected:
        raise HTTPException(status_code=503, detail="Private chat API is not configured")
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid API key")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coaching_spheres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coaching_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sphere_id INTEGER NOT NULL REFERENCES coaching_spheres(id),
            score INTEGER NOT NULL CHECK(score BETWEEN 0 AND 10),
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coaching_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            first_step TEXT NOT NULL DEFAULT '',
            target_date TEXT,
            status TEXT NOT NULL DEFAULT 'planned',
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
    """)
    return conn


class SphereInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class ScoreInput(BaseModel):
    sphere: str = Field(min_length=1, max_length=80)
    score: int = Field(ge=0, le=10)
    note: str = Field(default="", max_length=2000)


class GoalInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    first_step: str = Field(default="", max_length=2000)
    target_date: date | None = None


class GoalStatusInput(BaseModel):
    status: Literal["planned", "in_progress", "done", "paused"]


class ChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=6000)


@router.get("/status", dependencies=[Depends(require_api_key)])
def private_api_status():
    return {"status": "ok", "api_version": "v1", "scope": "single-owner"}


@router.get("/wheel", dependencies=[Depends(require_api_key)])
def read_wheel():
    with connect() as conn:
        spheres = conn.execute("SELECT id, name FROM coaching_spheres ORDER BY id").fetchall()
        result = []
        for sphere in spheres:
            scores = conn.execute(
                "SELECT score, note, created_at FROM coaching_scores WHERE sphere_id=? ORDER BY id",
                (sphere["id"],),
            ).fetchall()
            result.append({
                "name": sphere["name"],
                "history": [dict(row) for row in scores],
                "current_score": scores[-1]["score"] if scores else None,
            })
    return {"spheres": result}


@router.post("/wheel/spheres", dependencies=[Depends(require_api_key)])
def add_sphere(body: SphereInput):
    name = " ".join(body.name.split())
    if not name:
        raise HTTPException(status_code=422, detail="Sphere name cannot be blank")
    with connect() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO coaching_spheres(name, created_at) VALUES (?, ?)",
                (name, datetime.now(timezone.utc).isoformat()),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="Sphere already exists") from exc
        sphere_id = cursor.lastrowid
    return {"id": sphere_id, "name": name}


@router.post("/wheel/scores", dependencies=[Depends(require_api_key)])
def add_score(body: ScoreInput):
    name = " ".join(body.sphere.split())
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        row = conn.execute("SELECT id FROM coaching_spheres WHERE name=?", (name,)).fetchone()
        if row is None:
            cursor = conn.execute(
                "INSERT INTO coaching_spheres(name, created_at) VALUES (?, ?)", (name, now)
            )
            sphere_id = cursor.lastrowid
        else:
            sphere_id = row["id"]
        cursor = conn.execute(
            "INSERT INTO coaching_scores(sphere_id, score, note, created_at) VALUES (?, ?, ?, ?)",
            (sphere_id, body.score, body.note, now),
        )
    return {"id": cursor.lastrowid, "sphere": name, "score": body.score, "saved_at": now}


@router.get("/goals", dependencies=[Depends(require_api_key)])
def list_goals():
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, title, first_step, target_date, status, created_at, completed_at "
            "FROM coaching_goals ORDER BY COALESCE(target_date, '9999-12-31'), id"
        ).fetchall()
    return {"goals": [dict(row) for row in rows]}


@router.post("/goals", dependencies=[Depends(require_api_key)])
def create_goal(body: GoalInput):
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO coaching_goals(title, first_step, target_date, created_at) VALUES (?, ?, ?, ?)",
            (body.title.strip(), body.first_step.strip(), body.target_date.isoformat() if body.target_date else None, now),
        )
    return {"id": cursor.lastrowid, "title": body.title.strip(), "target_date": body.target_date, "status": "planned"}


@router.patch("/goals/{goal_id}")
def update_goal(goal_id: int, body: GoalStatusInput, _: None = Depends(require_api_key)):
    completed_at = datetime.now(timezone.utc).isoformat() if body.status == "done" else None
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE coaching_goals SET status=?, completed_at=? WHERE id=?",
            (body.status, completed_at, goal_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Goal not found")
    return {"id": goal_id, "status": body.status}


@router.post("/chat", dependencies=[Depends(require_api_key)])
async def chat(body: ChatInput):
    """Send one reflection message to the configured dialogue engine."""
    settings = get_settings()
    incoming = IncomingMessage(
        channel=Channel.TELEGRAM,
        external_user_id="private-chatgpt-action",
        text=body.message,
    )
    reply = await respond(incoming)
    return {"reply": reply.text}
