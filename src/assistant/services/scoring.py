from __future__ import annotations

from dataclasses import dataclass

from assistant.config.settings import Settings
from assistant.db.models import EnvelopeORM
from assistant.services.embeddings import model_embed, semantic_similarity, similarity

import logging
logger = logging.getLogger(__name__)

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

    def score(
        self,
        raw_text: str,
        card_keywords: list[str],
        envelope: EnvelopeORM,
        card_embedding: list[float] | None = None,
        assignee: str | None = None,
    ) -> tuple[float, str]:
        env_text = f"{envelope.name} {envelope.summary or ''}".strip()
        card_vec = card_embedding if card_embedding is not None else model_embed(raw_text, settings=self.settings)
        env_vec = envelope.embedding_vector_json or []
        if card_vec and env_vec:
            sim = similarity(card_vec, env_vec)
            logger.debug("EnvelopeScorer: similarity=%s for envelope=%s", sim, envelope.name)
        else:
            sim = semantic_similarity(raw_text, env_text, settings=self.settings)
            logger.debug("EnvelopeScorer: semantic_similarity=%s for envelope=%s", sim, envelope.name)

        envelope_keywords = [w.lower() for w in (envelope.keywords_json or []) if w]
        if not envelope_keywords:
            envelope_keywords = [w.lower() for w in env_text.split() if w]
        kscore = self._overlap(card_keywords, envelope_keywords)
        assignee_bonus = 0.0
        if assignee:
            normalized = assignee.strip().lower()
            if normalized and (
                normalized in " ".join(envelope_keywords)
                or normalized in (envelope.summary or "").lower()
                or normalized in envelope.name.lower()
            ):
                assignee_bonus = 1.0
        final = (
            self.settings.embedding_weight * sim
            + self.settings.keyword_weight * kscore
            + self.settings.entity_weight * assignee_bonus
        )
        return final, f"embedding={sim:.2f}, keyword={kscore:.2f}, assignee={assignee_bonus:.2f}"

    def choose_best(
        self,
        raw_text: str,
        card_keywords: list[str],
        envelopes: list[EnvelopeORM],
        card_embedding: list[float] | None = None,
        assignee: str | None = None,
    ) -> EnvelopeScore:
        if not envelopes:
            return EnvelopeScore(envelope=None, score=0.0, reason="no envelopes available")
        best_env = None
        best_score = -1.0
        best_reason = ""
        for envelope in envelopes:
            score, reason = self.score(
                raw_text, card_keywords, envelope, card_embedding=card_embedding, assignee=assignee
            )
            logger.debug("EnvelopeScorer: score=%s, reason=%s for envelope=%s", score, reason, envelope.name)
            if score > best_score:
                best_env = envelope
                best_score = score
                best_reason = reason
        return EnvelopeScore(envelope=best_env, score=max(best_score, 0.0), reason=best_reason)
