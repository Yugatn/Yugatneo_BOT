import asyncio
import pytest
import httpx

from app.services.telegraph_publisher import (
    TelegraphError, article_nodes, publish_public_article,
)


def test_article_nodes_are_plain_text_not_html():
    assert article_nodes(["<script>alert(1)</script>"]) == [
        {"tag": "p", "children": ["<script>alert(1)</script>"]}
    ]
    with pytest.raises(ValueError):
        article_nodes([" ", ""])


def test_public_article_publishing():
    def handler(request):
        import json
        payload = json.loads(request.content)
        assert request.url.path == "/createPage"
        assert payload["content"][0]["children"] == ["Educational content"]
        assert payload["return_content"] is False
        return httpx.Response(200, json={"ok": True, "result": {"url": "https://telegra.ph/example-01"}})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await publish_public_article(
                client, token="test-token", title="Development",
                paragraphs=["Educational content"])
    assert asyncio.run(run()) == "https://telegra.ph/example-01"


def test_reject_unexpected_url():
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"ok": True, "result": {"url": "https://evil.example/"}})
        )) as client:
            await publish_public_article(client, token="test-token", title="Test", paragraphs=["Content"])
    with pytest.raises(TelegraphError):
        asyncio.run(run())
