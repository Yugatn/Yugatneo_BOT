class MockLLM:
    async def generate_reply(self, *, user_text: str, conversation_summary: str = "") -> str:
        return (
            "Я могу помочь тебе исследовать ситуацию вопросами, а не ставить диагнозы. "
            "Что в описанном для тебя сейчас самое важное?"
        )
