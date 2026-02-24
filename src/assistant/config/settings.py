from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    database_url: str = Field(default="sqlite:///assistant.db", alias="DATABASE_URL")
    timezone: str = Field(default="UTC", alias="TIMEZONE")

    envelope_assign_threshold: float = Field(default=0.55, alias="ENVELOPE_ASSIGN_THRESHOLD")
    embedding_weight: float = Field(default=0.40, alias="EMBEDDING_WEIGHT")
    keyword_weight: float = Field(default=0.35, alias="KEYWORD_WEIGHT")
    entity_weight: float = Field(default=0.25, alias="ENTITY_WEIGHT")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
