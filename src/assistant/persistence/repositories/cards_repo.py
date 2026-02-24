from datetime import datetime

from sqlalchemy.orm import Session

from assistant.persistence.models import CardORM


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
        envelope_id: int | None,
    ) -> CardORM:
        card = CardORM(
            raw_text=raw_text,
            card_type=card_type,
            description=description,
            due_at=due_at,
            assignee_text=assignee_text,
            keywords_json=keywords,
            envelope_id=envelope_id,
        )
        self.session.add(card)
        self.session.flush()
        return card

    def list_cards(self) -> list[CardORM]:
        return self.session.query(CardORM).order_by(CardORM.created_at.desc()).all()
