import time

import instructor
from openai import OpenAI

from assistant.config.settings import Settings
from assistant.domain.cards.models import EntityMention, ExtractedCard
from assistant.ml.extraction.prompts import SYSTEM_PROMPT, build_user_prompt
from assistant.ml.extraction.schemas import ExtractedCardSchema


class LLMExtractor:
    def __init__(self, settings: Settings):
        self.settings = settings
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        self.client = instructor.from_openai(OpenAI(api_key=settings.openai_api_key))

    def extract(self, raw_text: str) -> tuple[ExtractedCard, int]:
        start = time.perf_counter()
        response = self.client.chat.completions.create(
            model=self.settings.openai_model,
            response_model=ExtractedCardSchema,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(raw_text)},
            ],
        )
        latency_ms = int((time.perf_counter() - start) * 1000)

        card = ExtractedCard(
            card_type=response.card_type,
            description=response.description.strip(),
            date_text=response.date_text,
            assignee=response.assignee,
            context_keywords=[k.strip().lower() for k in response.context_keywords if k.strip()],
            entities=[
                EntityMention(
                    entity_type=e.entity_type,
                    value=e.value.strip(),
                    role=e.role,
                    confidence=e.confidence,
                )
                for e in response.entities
                if e.value.strip()
            ],
            confidence=response.confidence,
        )
        return card, latency_ms
