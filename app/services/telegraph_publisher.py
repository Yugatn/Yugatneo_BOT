"""Telegraph publication of public, non-personal educational articles.

Only caller-supplied public content is accepted. Never send user reflections,
assessment results, conversation transcripts, or identifying data.
"""
from __future__ import annotations

import re
import httpx

TELEGRAPH_API = "https://api.telegra.ph"
SAFE_KEY = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


class TelegraphError(RuntimeError):
    pass


def article_nodes(paragraphs: list[str]) -> list[dict]:
    nodes: list[dict] = []
    for paragraph in paragraphs:
        text = paragraph.strip()
        if text:
            nodes.append({"tag": "p", "children": [text]})
    if not nodes:
        raise ValueError("Article content is empty")
    return nodes


async def publish_public_article(
    client: httpx.AsyncClient, *, token: str, title: str,
    paragraphs: list[str], author_name: str = "Yugatneo BOT",
) -> str:
    """Publish a PUBLIC Telegraph page. Caller must enforce content allowlist."""
    if not token.strip():
        raise ValueError("Telegraph access token is not configured")
    if not 1 <= len(title.strip()) <= 256:
        raise ValueError("Invalid article title")
    nodes = article_nodes(paragraphs)
    response = await client.post(
        f"{TELEGRAPH_API}/createPage",
        json={
            "access_token": token,
            "title": title.strip(),
            "author_name": author_name,
            "content": nodes,
            "return_content": False,
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok") or not payload.get("result", {}).get("url"):
        raise TelegraphError("Telegraph did not accept the publication")
    url = payload["result"]["url"]
    if not isinstance(url, str) or not url.startswith("https://telegra.ph/"):
        raise TelegraphError("Unexpected Telegraph article URL")
    return url
