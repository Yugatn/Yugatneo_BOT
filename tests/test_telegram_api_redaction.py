import asyncio

import httpx
import pytest

from app.telegram_polling import api


@pytest.mark.parametrize("payload", [[], None, {"ok": False}, {"ok": True}])
def test_telegram_api_redacts_malformed_response(payload):
    token = "sensitive-test-token"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=payload)
    )

    async def scenario():
        async with httpx.AsyncClient(transport=transport) as client:
            await api(client, token, "sendMessage", {"text": "synthetic"})

    with pytest.raises(RuntimeError) as exc:
        asyncio.run(scenario())
    assert "details redacted" in str(exc.value)
    assert token not in str(exc.value)


def test_telegram_http_error_redacts_request_url():
    token = "private-synthetic-token"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(403, json={"ok": False})
    )

    async def scenario():
        async with httpx.AsyncClient(transport=transport) as client:
            await api(client, token, "sendMessage")

    with pytest.raises(RuntimeError) as exc:
        asyncio.run(scenario())
    assert token not in str(exc.value)
    assert "sendMessage failed" in str(exc.value)
