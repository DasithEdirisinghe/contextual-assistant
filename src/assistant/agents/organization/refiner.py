from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from assistant.config.settings import Settings
from assistant.db.models import CardORM, EnvelopeORM
from assistant.llm.client import build_chat_model
from assistant.prompts import load_prompt_versioned, resolve_prompt_version

logger = logging.getLogger(__name__)


class EnvelopeRefineOutput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    summary: str = Field(min_length=1, max_length=300)


class EnvelopeRefiner:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.prompt_version = resolve_prompt_version("envelope_refine", settings.envelope_refine_prompt_version)
        logger.debug(
            "EnvelopeRefiner init: prompt_version=%s llm_provider=%s llm_model=%s",
            self.prompt_version,
            self.settings.effective_llm_provider,
            self.settings.effective_llm_model,
        )

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
        system_prompt = load_prompt_versioned(
            "envelope_refine",
            version=self.prompt_version,
        )
        human_payload = (
            f"Current envelope name: {envelope.name}\n\n"
            f"Current envelope summary: {envelope.summary or ''}\n\n"
            f"Current envelope keywords: {', '.join(envelope.keywords_json or [])}\n\n"
            f"Recent card descriptions:\n{card_lines or '- (none)'}"
        )
        try:
            llm = build_chat_model(self.settings)
            logger.debug(
                "EnvelopeRefiner refine: prompt_version=%s cards=%s human_payload_len=%s",
                self.prompt_version,
                len(cards),
                len(human_payload),
            )
            response = llm.with_structured_output(EnvelopeRefineOutput).invoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=human_payload)]
            )
            logger.debug("EnvelopeRefiner: response=%s", response)
            return EnvelopeRefineOutput(name=response.name.strip(), summary=response.summary.strip())
        except Exception:
            return self._fallback(envelope, cards)
