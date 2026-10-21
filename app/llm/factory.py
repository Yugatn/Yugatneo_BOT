from app.core.config import get_settings
from app.llm.mock import MockLLM


def get_llm():
    settings = get_settings()
    if settings.llm_provider.lower() == "openai":
        # Keep imports lazy so the project runs without OpenAI installed or a key.
        from app.llm.openai_provider import OpenAIProvider
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)
    return MockLLM()
