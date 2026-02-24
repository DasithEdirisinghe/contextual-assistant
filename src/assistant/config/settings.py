from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    llm_api_key: Optional[str] = Field(default=None, alias="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_base_url: Optional[str] = Field(default=None, alias="LLM_BASE_URL")
    database_url: str = Field(default="sqlite:///assistant.db", alias="DATABASE_URL")
    timezone: str = Field(default="UTC", alias="TIMEZONE")
    debug_mode: bool = Field(default=False, alias="DEBUG_MODE")

    envelope_assign_threshold: float = Field(default=0.55, alias="ENVELOPE_ASSIGN_THRESHOLD")
    embedding_weight: float = Field(default=0.40, alias="EMBEDDING_WEIGHT")
    keyword_weight: float = Field(default=0.35, alias="KEYWORD_WEIGHT")
    entity_weight: float = Field(default=0.25, alias="ENTITY_WEIGHT")

    @property
    def effective_llm_provider(self) -> str:
        return (self.llm_provider or "openai").strip().lower()

    @property
    def effective_llm_model(self) -> str:
        return self.llm_model

    @property
    def effective_llm_api_key(self) -> Optional[str]:
        return self.llm_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
