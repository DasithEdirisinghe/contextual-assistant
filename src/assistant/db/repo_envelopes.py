from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from assistant.db.models import EnvelopeORM


class EnvelopesRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_envelopes(self) -> list[EnvelopeORM]:
        return self.session.query(EnvelopeORM).order_by(EnvelopeORM.updated_at.desc()).all()

    def get_by_name(self, name: str) -> EnvelopeORM | None:
        return self.session.query(EnvelopeORM).filter(EnvelopeORM.name == name).one_or_none()

    def get_by_id(self, envelope_id: int) -> EnvelopeORM | None:
        return self.session.query(EnvelopeORM).filter(EnvelopeORM.id == envelope_id).one_or_none()

    def create_envelope(self, name: str, summary: str | None = None) -> EnvelopeORM:
        envelope = EnvelopeORM(
            name=name,
            summary=summary,
            keywords_json=[],
            embedding_vector_json=[],
            card_count=0,
            last_card_at=None,
        )
        self.session.add(envelope)
        self.session.flush()
        return envelope

    def update_profile(
        self,
        envelope: EnvelopeORM,
        *,
        keywords: list[str],
        embedding_vector: list[float],
        card_count: int,
        last_card_at: datetime | None,
    ) -> EnvelopeORM:
        envelope.keywords_json = keywords
        envelope.embedding_vector_json = embedding_vector
        envelope.card_count = card_count
        envelope.last_card_at = last_card_at
        self.session.flush()
        return envelope

    def update_summary(self, envelope: EnvelopeORM, *, name: str, summary: str | None) -> EnvelopeORM:
        envelope.name = name
        envelope.summary = summary
        self.session.flush()
        return envelope
