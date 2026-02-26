from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from assistant.db.models import CardORM


class CardsRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_card(
        self,
        raw_text: str,
        card_type: str,
        description: str,
        due_at: datetime | None,
        assignee_text: str | None,
        keywords: list[str],
        reasoning_steps: list[str],
        envelope_id: int | None,
    ) -> CardORM:
        card = CardORM(
            raw_text=raw_text,
            card_type=card_type,
            description=description,
            due_at=due_at,
            assignee_text=assignee_text,
            keywords_json=keywords,
            reasoning_steps_json=reasoning_steps,
            envelope_id=envelope_id,
        )
        self.session.add(card)
        self.session.flush()
        return card

    def list_cards(self, limit: int | None = None) -> list[CardORM]:
        query = self.session.query(CardORM).order_by(CardORM.created_at.desc())
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def list_by_envelope(self, envelope_id: int, limit: int | None = None) -> list[CardORM]:
        query = self.session.query(CardORM).filter(CardORM.envelope_id == envelope_id).order_by(CardORM.created_at.desc())
        if limit is not None:
            query = query.limit(limit)
        return query.all()
