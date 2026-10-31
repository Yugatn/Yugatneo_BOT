"""Safety and isolation tests for opt-in Telegram Mini App coaching pilot."""
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app import miniapp_coaching_api as api
from app.services.miniapp_coaching import (
    SessionRegistry, SessionCapacity, UnknownSession, StaleTurn, PROMPTS,
)


TOKEN = "test-telegram-token"


def telegram_auth(user_id: int, *, date: int | None = None, token: str = TOKEN) -> dict:
    fields = {
        "auth_date": str(int(time.time()) if date is None else date),
        "user": json.dumps({"id": user_id}, separators=(",", ":")),
    }
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return {"Authorization": "tma " + urlencode(fields)}


@pytest.fixture
def client(monkeypatch, tmp_path):
    config = get_settings()
    monkeypatch.setattr(config, "telegram_bot_token", TOKEN)
    monkeypatch.setattr(config, "miniapp_coaching_enabled", True)
    monkeypatch.setattr(config, "database_url", f"sqlite:///{tmp_path}/rate.sqlite3")
    monkeypatch.setattr(api, "sessions", SessionRegistry())
    with TestClient(app) as c:
        yield c


def payload(**overrides):
    return {
        "wheel_id": "main",
        "ray_id": "r0",
        "score": 0,
        "mode": "reframe",
        "consent_for_server_processing": True,
        "adult_attested": True,
        **overrides,
    }


def start(client, user=42, **overrides):
    return client.post("/api/v1/miniapp/coaching/sessions",
                       headers=telegram_auth(user), json=payload(**overrides))


def url(session_id):
    return "/api/v1/miniapp/coaching/sessions/" + session_id


def test_feature_is_disabled_by_default_and_is_fail_closed(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "miniapp_coaching_enabled", False)
    response = start(client)
    assert response.status_code == 503
    assert api.sessions.erase_all("42") == 0


def test_production_cannot_enable_unreviewed_coaching_even_with_flag(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "miniapp_coaching_enabled", True)
    monkeypatch.setattr(get_settings(), "app_env", "production")
    response = start(client)
    assert response.status_code == 503
    assert api.sessions.erase_all("42") == 0
    monkeypatch.setattr(get_settings(), "app_env", "custom-production-alias")
    assert start(client).status_code == 503


def test_auth_missing_invalid_and_expired(client):
    endpoint = "/api/v1/miniapp/coaching/sessions"
    assert client.post(endpoint, json=payload()).status_code == 401
    assert client.post(endpoint, headers=telegram_auth(42, token="bad"), json=payload()).status_code == 401
    assert client.post(endpoint, headers=telegram_auth(42, date=int(time.time())-7200), json=payload()).status_code == 401


def test_explicit_consent_adult_attestation_and_scoped_wheels(client):
    assert start(client, consent_for_server_processing=False).status_code == 403
    assert start(client, adult_attested=False).status_code == 403
    assert start(client, wheel_id="destructiveness").status_code == 422
    assert start(client, wheel_id="sexuality").status_code == 422
    assert start(client, wheel_id="fear").status_code == 422
    assert start(client, ray_id="private narrative").status_code == 422
    assert start(client, ray_id="r9").status_code == 422
    assert start(client, wheel_id="work", ray_id="r8").status_code == 422
    assert start(client, wheel_id="main", ray_id="r8").status_code == 201
    assert start(client, score=11).status_code == 422
    assert start(client, score=True).status_code == 422
    assert start(client, extra_user_id="other").status_code == 422
    assert start(client, score=None).status_code == 201
    assert start(client, score=0).status_code == 201


def test_owner_isolation_on_read_turn_and_delete(client):
    item = start(client, user=42).json()
    sid = item["session_id"]
    assert len(sid) == 32
    assert item["step"] == 0 and item["transcript_persisted"] is False
    assert client.get(url(sid), headers=telegram_auth(43)).status_code == 404
    attempt = client.post(url(sid)+"/turns", headers=telegram_auth(43),
                          json={"expected_step": 0, "action": "answer", "text": "secret"})
    assert attempt.status_code == 404
    assert client.delete(url(sid), headers=telegram_auth(43)).status_code == 404
    assert client.get(url(sid), headers=telegram_auth(42)).json()["step"] == 0
    okay = client.post(url(sid)+"/turns", headers=telegram_auth(42),
                       json={"expected_step": 0, "action": "answer", "text": "Мой личный ответ"})
    assert okay.status_code == 200
    assert okay.json()["step"] == 1
    assert "Мой личный ответ" not in str(okay.json())
    assert "Мой личный ответ" not in repr(api.sessions.status("42", sid))


def test_repeated_steps_are_rejected_without_double_advancement(client):
    sid = start(client).json()["session_id"]
    request = {"expected_step": 0, "action": "skip"}
    assert client.post(url(sid)+"/turns", headers=telegram_auth(42), json=request).json()["step"] == 1
    assert client.post(url(sid)+"/turns", headers=telegram_auth(42), json=request).status_code == 409
    assert client.get(url(sid), headers=telegram_auth(42)).json()["step"] == 1
    assert client.post(url(sid)+"/turns", headers=telegram_auth(42), json={
        "expected_step": 1, "action": "skip", "text": "should not be accepted"}).status_code == 422


def test_finish_and_manual_stop_erase_without_persistence(client):
    sid = start(client, mode="reflection").json()["session_id"]
    for step in range(len(PROMPTS["reflection"])):
        result = client.post(url(sid)+"/turns", headers=telegram_auth(42),
                             json={"expected_step": step, "action": "skip"})
        assert result.status_code == 200
        assert result.json()["finished"] == (step == len(PROMPTS["reflection"])-1)
    assert client.get(url(sid), headers=telegram_auth(42)).status_code == 404
    sid2 = start(client).json()["session_id"]
    response = client.post(url(sid2)+"/turns", headers=telegram_auth(42),
                           json={"expected_step": 0, "action": "stop"})
    assert response.status_code == 200 and response.json()["finished"] is True
    assert client.get(url(sid2), headers=telegram_auth(42)).status_code == 404


def test_crisis_handoff_ends_coaching_and_is_not_trusted_as_detection(client):
    sid = start(client).json()["session_id"]
    response = client.post(url(sid)+"/turns", headers=telegram_auth(42), json={
        "expected_step": 0, "action": "answer",
        "text": "Я собираюсь убить себя сегодня",
    })
    assert response.status_code == 200
    assert response.json()["safety"] == "immediate"
    assert response.json()["finished"] is True
    assert "экстренную службу" in response.json()["handoff"]
    assert client.get(url(sid), headers=telegram_auth(42)).status_code == 404


def test_erase_all_only_removes_authenticated_owner_sessions(client):
    alice = start(client, user=42).json()["session_id"]
    bob = start(client, user=43).json()["session_id"]
    assert client.delete("/api/v1/miniapp/coaching/sessions",
                         headers=telegram_auth(42)).status_code == 204
    assert client.get(url(alice), headers=telegram_auth(42)).status_code == 404
    assert client.get(url(bob), headers=telegram_auth(43)).status_code == 200


def test_no_automatic_ai_calls_or_unrestricted_cors(client):
    sid = start(client).json()["session_id"]
    assert client.get(url(sid), headers=telegram_auth(42)).headers["cache-control"] == "no-store"
    res = client.options(url(sid), headers={"Origin":"https://untrusted.example",
                                            "Access-Control-Request-Method":"GET"})
    assert not res.headers.get("access-control-allow-origin")
    assert "external_user_id" not in json.dumps(client.get(url(sid), headers=telegram_auth(42)).json())


def test_registry_prunes_expired_sessions_and_caps_capacity():
    now = [100.0]
    registry = SessionRegistry(clock=lambda:now[0], ttl_seconds=30, max_sessions=2, max_per_user=1)
    sid, _ = registry.start("alice", "coaching")
    with pytest.raises(SessionCapacity):
        registry.start("alice", "coaching")
    bob, _ = registry.start("bob", "reflection")
    with pytest.raises(SessionCapacity):
        registry.start("charlie", "reflection")
    with pytest.raises(UnknownSession):
        registry.status("bob", sid)
    with pytest.raises(StaleTurn):
        registry.advance("alice", sid, expected_step=1, action="skip")
    now[0] += 31
    with pytest.raises(UnknownSession):
        registry.status("alice", sid)
    assert registry.erase_all("bob") == 0
    registry.start("alice", "reflection")
    assert bob not in registry._entries


def test_invalid_payload_does_not_leak_answer_in_error(client):
    sid=start(client).json()["session_id"]
    secret="PRIVATE-TEST-ANSWER"
    r=client.post(url(sid)+"/turns", headers=telegram_auth(42), json={
        "expected_step": 0, "action": "skip", "text": secret,
    })
    assert r.status_code == 422
    assert secret not in r.text
    assert client.get(url(sid), headers=telegram_auth(42)).json()["step"] == 0
