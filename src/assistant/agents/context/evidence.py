from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from assistant.db.models import CardORM, EnvelopeORM


@dataclass
class ContextEvidenceCard:
    card_id: int
    card_type: str
    description: str
    assignee: str | None
    keywords: list[str]
    due_at: datetime | None
    envelope_id: int | None
    envelope_name: str | None
    created_at: datetime


def _importance_score(card: CardORM) -> float:
    score = 0.0
    if card.card_type == "task":
        score += 2.0
    elif card.card_type == "reminder":
        score += 1.5
    if card.due_at is not None:
        score += 1.0
    if card.assignee_text:
        score += 0.6
    score += min(len(card.keywords_json or []), 5) * 0.15
    return score


def build_context_evidence(session: Session, *, max_cards: int = 12) -> list[ContextEvidenceCard]:
    cards = session.query(CardORM).order_by(CardORM.created_at.desc()).limit(120).all()
    if not cards:
        return []

    envelopes = session.query(EnvelopeORM).order_by(EnvelopeORM.card_count.desc(), EnvelopeORM.updated_at.desc()).limit(8).all()
    card_map = {c.id: c for c in cards}
    selected_ids: list[int] = []

    # Most recent globally.
    for card in cards[:6]:
        selected_ids.append(card.id)

    # Most important per active envelope.
    for env in envelopes:
        env_cards = [c for c in cards if c.envelope_id == env.id]
        if not env_cards:
            continue
        important = sorted(env_cards, key=_importance_score, reverse=True)[0]
        selected_ids.append(important.id)

    # Deduplicate in insertion order and cap.
    deduped: list[int] = []
    seen = set()
    for cid in selected_ids:
        if cid in seen:
            continue
        seen.add(cid)
        deduped.append(cid)
        if len(deduped) >= max_cards:
            break

    evidence: list[ContextEvidenceCard] = []
    for cid in deduped:
        card = card_map.get(cid)
        if card is None:
            continue
        envelope_name = card.envelope.name if card.envelope is not None else None
        evidence.append(
            ContextEvidenceCard(
                card_id=card.id,
                card_type=card.card_type,
                description=card.description,
                assignee=card.assignee_text,
                keywords=card.keywords_json or [],
                due_at=card.due_at,
                envelope_id=card.envelope_id,
                envelope_name=envelope_name,
                created_at=card.created_at,
            )
        )
    return evidence
