from __future__ import annotations

import logging

from langchain_openai import ChatOpenAI

from assistant.config.settings import Settings
from assistant.llm.types import LLMConfig

logger = logging.getLogger(__name__)

_PROVIDER_DEFAULT_BASE_URL = {
    "openai": None,
    "deepseek": "https://api.deepseek.com/v1",
    "ollama": "http://localhost:11434/v1",
    "openai_compatible": None,
}


def build_llm_config(settings: Settings) -> LLMConfig:
    provider = settings.effective_llm_provider
    model = settings.effective_llm_model
    base_url = settings.llm_base_url or _PROVIDER_DEFAULT_BASE_URL.get(provider)
    api_key = settings.effective_llm_api_key

    if provider in {"openai", "deepseek"} and not api_key:
        raise ValueError(f"LLM_API_KEY is required for provider '{provider}'")
    if provider == "openai_compatible" and (not api_key or not base_url):
        raise ValueError("LLM_BASE_URL and LLM_API_KEY are required for provider 'openai_compatible'")
    if provider == "ollama" and not api_key:
        api_key = "ollama"
    if provider not in _PROVIDER_DEFAULT_BASE_URL:
        raise ValueError(f"Unsupported provider '{provider}'. Supported: {', '.join(_PROVIDER_DEFAULT_BASE_URL)}")

    return LLMConfig(provider=provider, model=model, api_key=api_key, base_url=base_url)


def build_chat_model(settings: Settings) -> ChatOpenAI:
    cfg = build_llm_config(settings)
    logger.debug("Building chat model provider=%s model=%s base_url=%s", cfg.provider, cfg.model, cfg.base_url)
    return ChatOpenAI(
        model=cfg.model,
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        temperature=0,
        max_retries=1,
    )
