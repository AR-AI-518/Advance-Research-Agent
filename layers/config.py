from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = Field(validation_alias="OPENAI_API_KEY")
    base_model: str = "gpt-4.1-mini"
    fallback_model: str = "gpt-4.1-mini"

    langchain_api_key: str = Field(validation_alias="LANGCHAIN_API_KEY")
    langchain_project: str = "Production"
    langchain_tracing_v2: bool = True
    tavily_api_key=str

    max_retries: int = 3
    log_level: str = "INFO"
    rate_limit: str = "20/minute"
    app_env: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()