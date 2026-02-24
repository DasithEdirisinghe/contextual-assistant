from sqlalchemy.orm import Session

from assistant.persistence.models import EnvelopeORM


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
        envelope = EnvelopeORM(name=name, summary=summary)
        self.session.add(envelope)
        self.session.flush()
        return envelope
