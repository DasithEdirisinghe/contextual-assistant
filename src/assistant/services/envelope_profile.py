from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from assistant.config.settings import Settings
from assistant.db.models import CardORM
from assistant.services.embeddings import model_embed


@dataclass
class EnvelopeProfile:
    keywords: list[str]
    embedding_vector: list[float]
    card_count: int
    last_card_at: datetime | None


def _normalize_keywords(keywords: list[str]) -> list[str]:
    return [k.strip().lower() for k in keywords if k and k.strip()]


def _compute_keywords(cards: list[CardORM], limit: int = 12) -> list[str]:
    weighted = Counter()
    total = len(cards)
    for idx, card in enumerate(cards):
        recency_weight = 1.0 - (idx / max(total, 1)) * 0.5
        for kw in _normalize_keywords(card.keywords_json or [])[:8]:
            weighted[kw] += recency_weight
    return [kw for kw, _ in weighted.most_common(limit)]


def _mean_vector(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    size = len(vectors[0])
    if size == 0 or any(len(v) != size for v in vectors):
        return []
    sums = [0.0] * size
    for vec in vectors:
        for i, val in enumerate(vec):
            sums[i] += float(val)
    return [value / len(vectors) for value in sums]


def build_envelope_profile(cards: list[CardORM], settings: Settings) -> EnvelopeProfile:
    if not cards:
        return EnvelopeProfile(keywords=[], embedding_vector=[], card_count=0, last_card_at=None)

    keywords = _compute_keywords(cards)
    vectors = [model_embed(card.raw_text, settings=settings) for card in cards if card.raw_text]
    vectors = [vec for vec in vectors if vec]
    centroid = _mean_vector(vectors)
    last_card_at = max((card.created_at for card in cards if card.created_at), default=None)
    return EnvelopeProfile(
        keywords=keywords,
        embedding_vector=centroid,
        card_count=len(cards),
        last_card_at=last_card_at,
    )
