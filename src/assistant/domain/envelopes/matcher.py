from dataclasses import dataclass

from assistant.config.settings import Settings
from assistant.ml.embeddings.similarity import semantic_similarity
from assistant.persistence.models import EnvelopeORM


@dataclass
class EnvelopeMatchResult:
    envelope: EnvelopeORM | None
    score: float
    reason: str


class EnvelopeMatcher:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _keyword_overlap(self, a: list[str], b: list[str]) -> float:
        if not a or not b:
            return 0.0
        sa, sb = set(a), set(b)
        return len(sa.intersection(sb)) / len(sa.union(sb))

    def _entity_overlap(self, card_entities: list[str], env_entities: list[str]) -> float:
        return self._keyword_overlap(card_entities, env_entities)

    def score_envelope(
        self,
        card_description: str,
        card_keywords: list[str],
        card_entities: list[str],
        envelope: EnvelopeORM,
    ) -> tuple[float, str]:
        env_text = f"{envelope.name} {envelope.summary or ''}".strip()
        sim = semantic_similarity(card_description, env_text)

        env_keywords = [w.lower() for w in env_text.split() if w]
        kscore = self._keyword_overlap(card_keywords, env_keywords)

        env_entities = [token.lower() for token in (envelope.name or "").split() if token]
        escore = self._entity_overlap(card_entities, env_entities)

        final_score = (
            self.settings.embedding_weight * sim
            + self.settings.keyword_weight * kscore
            + self.settings.entity_weight * escore
        )
        reason = f"embedding={sim:.2f}, keyword={kscore:.2f}, entity={escore:.2f}"
        return final_score, reason

    def choose_best(
        self,
        card_description: str,
        card_keywords: list[str],
        card_entities: list[str],
        envelopes: list[EnvelopeORM],
    ) -> EnvelopeMatchResult:
        if not envelopes:
            return EnvelopeMatchResult(envelope=None, score=0.0, reason="no envelopes available")

        best_envelope = None
        best_score = -1.0
        best_reason = ""

        for envelope in envelopes:
            score, reason = self.score_envelope(card_description, card_keywords, card_entities, envelope)
            if score > best_score:
                best_score = score
                best_envelope = envelope
                best_reason = reason

        return EnvelopeMatchResult(envelope=best_envelope, score=max(best_score, 0.0), reason=best_reason)
