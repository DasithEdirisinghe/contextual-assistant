import logging

from assistant.config.settings import Settings
from assistant.domain.cards.models import ExtractedCard
from assistant.ml.extraction.fallback import FallbackExtractor
from assistant.ml.extraction.llm_client import LLMExtractor

logger = logging.getLogger(__name__)


class CardExtractionService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.fallback = FallbackExtractor()

    def extract(self, raw_text: str) -> tuple[ExtractedCard, str, int, bool, str | None]:
        if not self.settings.openai_api_key:
            card = self.fallback.extract(raw_text)
            return card, "fallback-rule", 0, True, None

        try:
            llm = LLMExtractor(self.settings)
            card, latency = llm.extract(raw_text)
            return card, self.settings.openai_model, latency, True, None
        except Exception as exc:  # noqa: BLE001
            logger.exception("LLM extraction failed; using fallback")
            card = self.fallback.extract(raw_text)
            return card, "fallback-rule", 0, False, str(exc)
