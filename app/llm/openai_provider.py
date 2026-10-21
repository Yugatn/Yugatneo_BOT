"""Optional OpenAI adapter. Install the openai package when you are ready to connect it."""
from app.llm.base import LLMProvider


class OpenAIProvider:
    def __init__(self, *, api_key: str, model: str | None = None):
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("Install the optional 'openai' package to use this provider") from exc
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model or "gpt-4.1-mini"

    async def generate_reply(self, *, user_text: str, conversation_summary: str = "") -> str:
        response = await self.client.responses.create(
            model=self.model,
            instructions=(
                "Ты — бережный помощник по коучингу, рефлексии и психообразованию. "
                "Не ставь диагнозов, не обещай лечение, не выдумывай факты о пользователе. "
                "Задавай по одному открытому вопросу и уважай отказ и автономию человека. "
                "Для самоисследования обусловленности помогай различать наблюдаемый факт, "
                "интерпретацию, эмоцию, телесную реакцию, потребность, социальное ожидание и выбор. "
                "Не объявляй скрытую причину поведения, не считай несогласие сопротивлением и "
                "не подталкивай к отказу от идентичности, лечения или отношений. Цель — расширить "
                "свободу осознанного выбора, а не стереть личность или память. "
                "При признаках непосредственной опасности сначала помоги обратиться к местным "
                "экстренным службам или доверенному человеку."
            ),
            input=f"Краткий контекст: {conversation_summary}\n\nСообщение пользователя: {user_text}",
        )
        return response.output_text
