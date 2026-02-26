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
    embedding_provider: str = Field(default="auto", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_api_key: Optional[str] = Field(default=None, alias="EMBEDDING_API_KEY")
    embedding_base_url: Optional[str] = Field(default=None, alias="EMBEDDING_BASE_URL")
    ingestion_prompt_version: Optional[str] = Field(default=None, alias="INGESTION_PROMPT_VERSION")
    envelope_refine_prompt_version: Optional[str] = Field(default=None, alias="ENVELOPE_REFINE_PROMPT_VERSION")
    context_update_prompt_version: Optional[str] = Field(default=None, alias="CONTEXT_UPDATE_PROMPT_VERSION")
    thinking_prompt_version: Optional[str] = Field(default=None, alias="THINKING_PROMPT_VERSION")
    thinking_output_dir: str = Field(default="data/thinking_runs", alias="THINKING_OUTPUT_DIR")
    thinking_max_cards: int = Field(default=200, alias="THINKING_MAX_CARDS")
    thinking_max_envelopes: int = Field(default=100, alias="THINKING_MAX_ENVELOPES")
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

    @property
    def effective_embedding_provider(self) -> str:
        return (self.embedding_provider or "auto").strip().lower()

    @property
    def effective_embedding_model(self) -> str:
        return self.embedding_model.strip()

    @property
    def effective_embedding_api_key(self) -> Optional[str]:
        return self.embedding_api_key or self.llm_api_key

    @property
    def effective_embedding_base_url(self) -> Optional[str]:
        return self.embedding_base_url or self.llm_base_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
