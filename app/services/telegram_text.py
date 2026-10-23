"""Split Telegram messages without silently discarding user report content."""
from __future__ import annotations

MAX_MESSAGE_LENGTH = 4000


def split_telegram_text(text: str, limit: int = MAX_MESSAGE_LENGTH) -> list[str]:
    if limit < 1:
        raise ValueError("limit must be positive")
    if not text:
        return [""]
    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        # Prefer an existing paragraph or line boundary without losing text.
        cut = remaining.rfind("\n", 0, limit + 1)
        if cut < 1:
            cut = limit
        else:
            cut += 1
        chunks.append(remaining[:cut])
        remaining = remaining[cut:]
    if remaining:
        chunks.append(remaining)
    return chunks
