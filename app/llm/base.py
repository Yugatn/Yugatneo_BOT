from typing import Protocol


class LLMProvider(Protocol):
    async def generate_reply(self, *, user_text: str, conversation_summary: str = "") -> str:
        """Generate a reply without assuming any particular vendor."""
        ...
