from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass

from sqlalchemy.orm import Session

from assistant.db.models import CardORM
from assistant.db.repo_context_snapshot import ContextSnapshotRepository


@dataclass
class DerivedContextItem:
    label: str
    strength: float
    mention_count: int


class ContextRepository:
    def __init__(self, session: Session):
        self.session = session

    def top_context_entities(self, limit: int = 10) -> list[DerivedContextItem]:
        """Derive context from cards only (assignees + keywords), no entity tables."""
        cards = self.session.query(CardORM).order_by(CardORM.created_at.desc()).limit(500).all()

        weighted_counts: Counter[str] = Counter()
        mentions: Counter[str] = Counter()

        # Recency-aware weighting: latest cards contribute higher signal.
        total = len(cards)
        for idx, card in enumerate(cards):
            recency_weight = 1.0 - (idx / max(total, 1)) * 0.5

            if card.assignee_text:
                label = f"person:{card.assignee_text}"
                weighted_counts[label] += 1.2 * recency_weight
                mentions[label] += 1

            for keyword in (card.keywords_json or [])[:5]:
                label = f"theme:{keyword}"
                weighted_counts[label] += 0.8 * recency_weight
                mentions[label] += 1

        top = weighted_counts.most_common(limit)
        return [
            DerivedContextItem(label=label, strength=float(strength), mention_count=int(mentions[label]))
            for label, strength in top
        ]

    def get_persisted_context(self) -> dict | None:
        snapshot = ContextSnapshotRepository(self.session).get_snapshot()
        if snapshot is None:
            return None
        try:
            return {
                "context": json.loads(snapshot.context_json),
                "focus_summary": snapshot.focus_summary,
                "updated_at": snapshot.updated_at.isoformat() if snapshot.updated_at else None,
            }
        except Exception:
            return None
