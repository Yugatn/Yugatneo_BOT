"""Read-only Telegram connection checks; all network activity is simulated."""
import asyncio
import json

import httpx
import pytest

from app.telegram_staging_probe import check_offline, check_online


def _run(token, handler):
    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), timeout=2
        ) as client:
            return await check_online(token, client)
    return asyncio.run(scenario())


def test_offline_requires_no_network_or_secret_output():
    result = check_offline("private-token")
    assert result["token_configured"]
    assert not result["online_check_performed"]
    assert not result["polling_preflight_passed"]
    assert not result["message_sent"]
    assert not result["public_release_approved"]
    assert "private-token" not in json.dumps(result)


def test_online_verifies_identity_and_no_webhook_without_sending():
    calls = []
    def handler(req):
        calls.append(req.url.path.rsplit("/", 1)[-1])
        if req.url.path.endswith("/getMe"):
            return httpx.Response(200, json={"ok": True, "result": {"is_bot": True, "username": "synthetic_bot"}})
        return httpx.Response(200, json={"ok": True, "result": {"url": "", "pending_update_count": 9}})
    report = _run("test-secret", handler)
    assert report["polling_preflight_passed"]
    assert calls == ["getMe", "getWebhookInfo"]
    assert report["message_sent"] is False
    assert report["public_release_approved"] is False
    assert "test-secret" not in json.dumps(report)


def test_online_active_webhook_is_a_blocker_and_url_is_redacted():
    private_url = "https://internal.example/private-secret"
    def handler(req):
        if req.url.path.endswith("/getMe"):
            return httpx.Response(200, json={"ok": True, "result": {"is_bot": True}})
        return httpx.Response(200, json={"ok": True, "result": {"url": private_url}})
    report = _run("test-secret", handler)
    assert not report["polling_preflight_passed"]
    assert report["check_error"] == "webhook_active_polling_conflict"
    assert private_url not in json.dumps(report)


@pytest.mark.parametrize("api_result", [
    {"ok": False, "description": "token-do-not-leak"},
    {"ok": True, "result": []},
    {"ok": True},
    [1, 2],
])
def test_malformed_identity_fails_closed_and_redacts(api_result):
    report = _run(
        "private-token",
        lambda request: httpx.Response(200, json=api_result),
    )
    assert not report["polling_preflight_passed"]
    assert report["check_error"] == "telegram_identity_check_failed"
    assert "private-token" not in json.dumps(report)
    assert "token-do-not-leak" not in json.dumps(report)


def test_http_failure_never_leaks_url_or_token():
    report = _run(
        "hidden-token",
        lambda req: httpx.Response(403, text="hidden-token"),
    )
    assert report["check_error"] == "telegram_identity_check_failed"
    assert "hidden-token" not in json.dumps(report)


def test_transport_exception_never_leaks_url_or_token():
    def handler(req):
        raise httpx.ConnectError("botsecret in URL " + str(req.url), request=req)
    report = _run("botsecret", handler)
    assert not report["polling_preflight_passed"]
    assert "botsecret" not in json.dumps(report)


def test_absent_token_does_not_contact_telegram():
    calls = []
    result = _run(None, lambda req: calls.append(req) or httpx.Response(200))
    assert not calls
    assert result["check_error"] == "missing_bot_token"
    assert not result["online_check_performed"]


def test_webhook_query_failure_is_not_treated_as_inactive():
    def handler(req):
        if req.url.path.endswith("/getMe"):
            return httpx.Response(200, json={"ok": True, "result": {"is_bot": True}})
        return httpx.Response(200, json={"ok": False, "description": "hidden"})
    result = _run("example-token", handler)
    assert result["telegram_identity_verified"]
    assert not result["webhook_inactive"]
    assert result["check_error"] == "webhook_check_failed"
