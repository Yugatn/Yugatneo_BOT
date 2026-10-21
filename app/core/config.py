from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Yugatneo BOT"
    app_env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str = "sqlite:///./yugatneo_bot.sqlite3"
    free_question_limit: int = 7
    llm_provider: str = "mock"
    openai_api_key: str | None = None
    openai_model: str | None = None
    telegram_bot_token: str | None = None
    meta_verify_token: str | None = None
    meta_access_token: str | None = None
    meta_app_secret: str | None = None
    instagram_account_id: str | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_business_account_id: str | None = None
    public_base_url: str | None = None
    subscription_provider: str = "manual"
    turnstile_secret_key: str | None = None
    ticket_signing_secret: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
