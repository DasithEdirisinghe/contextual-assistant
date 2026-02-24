from __future__ import annotations

from dataclasses import dataclass

from assistant.config.settings import Settings
from assistant.db.models import EnvelopeORM
from assistant.services.embeddings import semantic_similarity


@dataclass
class EnvelopeScore:
    envelope: EnvelopeORM | None
    score: float
    reason: str


class EnvelopeScorer:
    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def _overlap(a: list[str], b: list[str]) -> float:
        if not a or not b:
            return 0.0
        sa, sb = set(a), set(b)
        return len(sa.intersection(sb)) / len(sa.union(sb))

    def score(self, card_description: str, card_keywords: list[str], card_entities: list[str], envelope: EnvelopeORM) -> tuple[float, str]:
        env_text = f"{envelope.name} {envelope.summary or ''}".strip()
        sim = semantic_similarity(card_description, env_text)
        kscore = self._overlap(card_keywords, [w.lower() for w in env_text.split() if w])
        escore = self._overlap(card_entities, [w.lower() for w in envelope.name.split() if w])
        final = (
            self.settings.embedding_weight * sim
            + self.settings.keyword_weight * kscore
            + self.settings.entity_weight * escore
        )
        return final, f"embedding={sim:.2f}, keyword={kscore:.2f}, entity={escore:.2f}"

    def choose_best(self, card_description: str, card_keywords: list[str], card_entities: list[str], envelopes: list[EnvelopeORM]) -> EnvelopeScore:
        if not envelopes:
            return EnvelopeScore(envelope=None, score=0.0, reason="no envelopes available")
        best_env = None
        best_score = -1.0
        best_reason = ""
        for envelope in envelopes:
            score, reason = self.score(card_description, card_keywords, card_entities, envelope)
            if score > best_score:
                best_env = envelope
                best_score = score
                best_reason = reason
        return EnvelopeScore(envelope=best_env, score=max(best_score, 0.0), reason=best_reason)
