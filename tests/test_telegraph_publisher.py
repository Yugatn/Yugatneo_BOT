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


@pytest.mark.asyncio
async def test_public_article_publishing():
    def handler(request):
        import json
        payload = json.loads(request.content)
        assert request.url.path == "/createPage"
        assert payload["content"][0]["children"] == ["Educational content"]
        assert payload["return_content"] is False
        return httpx.Response(200, json={"ok": True, "result": {"url": "https://telegra.ph/example-01"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        url = await publish_public_article(
            client, token="test-token", title="Development",
            paragraphs=["Educational content"])
    assert url == "https://telegra.ph/example-01"


@pytest.mark.asyncio
async def test_reject_unexpected_url():
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json={"ok": True, "result": {"url": "https://evil.example/"}})
    )) as client:
        with pytest.raises(TelegraphError):
            await publish_public_article(client, token="test-token", title="Test", paragraphs=["Content"])
