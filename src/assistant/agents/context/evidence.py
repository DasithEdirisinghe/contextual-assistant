from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import case, func
from sqlalchemy.orm import Session, aliased

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


def build_context_evidence(session: Session, *, max_cards: int = 12) -> list[ContextEvidenceCard]:
    # Query A: latest global cards (fixed window used by existing behavior).
    latest_ids = [
        row[0]
        for row in (
            session.query(CardORM.id)
            .order_by(CardORM.created_at.desc())
            .limit(6)
            .all()
        )
    ]
    if not latest_ids:
        return []

    # Query B: active envelopes.
    active_envelope_ids = [
        row[0]
        for row in (
            session.query(EnvelopeORM.id)
            .order_by(EnvelopeORM.card_count.desc(), EnvelopeORM.updated_at.desc())
            .limit(8)
            .all()
        )
    ]

    selected_ids = list(latest_ids)

    # Query C: top-important card per active envelope using window function.
    if active_envelope_ids:
        keyword_count = func.coalesce(func.json_array_length(CardORM.keywords_json), 0)
        importance_score = (
            case((CardORM.card_type == "task", 2.0), (CardORM.card_type == "reminder", 1.5), else_=0.0)
            + case((CardORM.due_at.is_not(None), 1.0), else_=0.0)
            + case((CardORM.assignee_text.is_not(None), 0.6), else_=0.0)
            + case((keyword_count > 5, 5), else_=keyword_count) * 0.15
        )

        ranked = (
            session.query(
                CardORM.id.label("card_id"),
                CardORM.envelope_id.label("envelope_id"),
                func.row_number()
                .over(
                    partition_by=CardORM.envelope_id,
                    order_by=(importance_score.desc(), CardORM.created_at.desc()),
                )
                .label("rn"),
            )
            .filter(CardORM.envelope_id.in_(active_envelope_ids))
            .subquery()
        )

        ranked_alias = aliased(ranked)
        top_per_env_ids = [
            row[0]
            for row in (
                session.query(ranked_alias.c.card_id)
                .filter(ranked_alias.c.rn == 1)
                .order_by(ranked_alias.c.envelope_id.asc())
                .all()
            )
        ]
        selected_ids.extend(top_per_env_ids)

    # Deduplicate in insertion order and cap.
    deduped_ids: list[int] = []
    seen: set[int] = set()
    for cid in selected_ids:
        if cid in seen:
            continue
        seen.add(cid)
        deduped_ids.append(cid)
        if len(deduped_ids) >= max_cards:
            break

    if not deduped_ids:
        return []

    # Query D: fetch selected cards + envelope name in one query.
    rows = (
        session.query(CardORM, EnvelopeORM.name)
        .outerjoin(EnvelopeORM, CardORM.envelope_id == EnvelopeORM.id)
        .filter(CardORM.id.in_(deduped_ids))
        .all()
    )
    by_id = {
        card.id: ContextEvidenceCard(
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
        for card, envelope_name in rows
    }
    return [by_id[cid] for cid in deduped_ids if cid in by_id]
