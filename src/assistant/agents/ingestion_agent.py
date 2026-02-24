from __future__ import annotations

import logging
from typing import Optional

from assistant.agents.ingestion.fallback import FallbackExtractor
from assistant.agents.ingestion.llm_pipeline import IngestionLLMPipeline
from assistant.config.settings import Settings
from assistant.schemas.card import ExtractedCard

logger = logging.getLogger(__name__)


class IngestionAgent:
    """Extraction agent: raw note -> ExtractedCard."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.fallback = FallbackExtractor()

    def extract(self, raw_text: str) -> tuple[ExtractedCard, str, int, bool, Optional[str]]:
        provider = self.settings.effective_llm_provider
        has_llm_key = bool(self.settings.effective_llm_api_key)
        llm_disabled = provider in {"openai", "deepseek", "openai_compatible"} and not has_llm_key

        if llm_disabled:
            card = self.fallback.extract(raw_text)
            return card, "fallback-rule", 0, True, None

        try:
            llm = IngestionLLMPipeline(self.settings)
            card, latency = llm.extract(raw_text)
            return card, f"{provider}:{self.settings.effective_llm_model}", latency, True, None
        except Exception as exc:  # noqa: BLE001
            logger.exception("IngestionAgent: LLM extraction failed, using fallback")
            card = self.fallback.extract(raw_text)
            return card, "fallback-rule", 0, False, str(exc)
