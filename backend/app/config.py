from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    DATABASE_URL: str = "postgresql://debate_user:debate_pass@localhost:5432/ai_debate"

    REDIS_URL: str = "redis://localhost:6379/0"
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:4173",
    ]

    # llm api keys
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    # jwt
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
