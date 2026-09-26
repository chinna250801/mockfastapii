from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "mockfastapi"
    secret_key: str = "change-me-to-a-long-random-string"
    access_token_expire_minutes: int = 60
    database_url: str = "postgresql+psycopg://chinna@/mockfastapi?host=/tmp"

    # AI — real API only (no stub). Set provider + key.
    ai_provider: str = "openai"  # openai | gemini
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
