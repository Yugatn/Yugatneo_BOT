from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import chat_control
from app.main import app


def test_private_api_rejects_missing_key():
    client = TestClient(app)
    response = client.get("/api/v1/status")
    assert response.status_code == 401


def test_wheel_score_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(chat_control, "DB_PATH", tmp_path / "test.sqlite3")
    monkeypatch.setattr(
        chat_control,
        "get_settings",
        lambda: SimpleNamespace(chat_control_api_key="test-secret"),
    )
    client = TestClient(app)
    headers = {"X-API-Key": "test-secret"}

    saved = client.post(
        "/api/v1/wheel/scores",
        headers=headers,
        json={"sphere": "Творчество", "score": 7, "note": "Выделять время регулярно"},
    )
    assert saved.status_code == 200
    assert saved.json()["score"] == 7

    wheel = client.get("/api/v1/wheel", headers=headers)
    assert wheel.status_code == 200
    assert wheel.json()["spheres"][0]["name"] == "Творчество"
    assert wheel.json()["spheres"][0]["current_score"] == 7


def test_goal_create_and_status_update(tmp_path, monkeypatch):
    monkeypatch.setattr(chat_control, "DB_PATH", tmp_path / "goals.sqlite3")
    monkeypatch.setattr(
        chat_control,
        "get_settings",
        lambda: SimpleNamespace(chat_control_api_key="test-secret"),
    )
    client = TestClient(app)
    headers = {"X-API-Key": "test-secret"}

    created = client.post(
        "/api/v1/goals",
        headers=headers,
        json={"title": "Начать тренировку", "first_step": "Выбрать 20 минут", "target_date": "2026-11-01"},
    )
    assert created.status_code == 200
    goal_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/goals/{goal_id}",
        headers=headers,
        json={"status": "in_progress"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"
