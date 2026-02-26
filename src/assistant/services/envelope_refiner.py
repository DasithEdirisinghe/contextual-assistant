from __future__ import annotations

from pydantic import BaseModel, Field

from assistant.config.settings import Settings
from assistant.db.models import CardORM, EnvelopeORM
from assistant.llm.client import build_chat_model
from assistant.prompts import load_prompt

import logging

logger = logging.getLogger(__name__)


class EnvelopeRefineOutput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    summary: str = Field(min_length=1, max_length=300)


class EnvelopeRefiner:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _llm_enabled(self) -> bool:
        provider = self.settings.effective_llm_provider
        if provider in {"openai", "deepseek", "openai_compatible"} and not self.settings.effective_llm_api_key:
            return False
        return True

    @staticmethod
    def _fallback(envelope: EnvelopeORM, cards: list[CardORM]) -> EnvelopeRefineOutput:
        keywords = envelope.keywords_json or []
        if keywords:
            title = keywords[0].replace("_", " ").title()
        else:
            title = (envelope.name or "General").strip()[:255]
        recent = [c.description.strip() for c in cards[:3] if c.description]
        summary = "; ".join(recent)[:300] if recent else (envelope.summary or "General context")[:300]
        return EnvelopeRefineOutput(name=title, summary=summary or "General context")

    def refine(self, envelope: EnvelopeORM, cards: list[CardORM]) -> EnvelopeRefineOutput:
        if not cards or not self._llm_enabled():
            return self._fallback(envelope, cards)

        card_lines = "\n".join(
            f"- {card.description}" for card in cards[:12] if card.description
        ).strip()
        prompt = load_prompt(
            "envelope_refine.jinja",
            envelope_name=envelope.name,
            envelope_summary=envelope.summary or "",
            card_descriptions=card_lines or "- (none)",
            keywords=", ".join(envelope.keywords_json or []),
        )
        try:
            llm = build_chat_model(self.settings)
            response = llm.with_structured_output(EnvelopeRefineOutput).invoke(prompt)
            logger.debug("EnvelopeRefiner: response=%s", response)
            return EnvelopeRefineOutput(name=response.name.strip(), summary=response.summary.strip())
        except Exception:
            return self._fallback(envelope, cards)
