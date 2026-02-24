from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from assistant.db.models import CardEntityORM, ContextSignalORM, EntityORM


class ContextRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_entity(self, entity_type: str, canonical_name: str, aliases: list[str] | None = None) -> EntityORM:
        entity = (
            self.session.query(EntityORM)
            .filter(EntityORM.entity_type == entity_type, EntityORM.canonical_name == canonical_name)
            .one_or_none()
        )
        if entity:
            if aliases:
                entity.aliases_json = sorted(set(entity.aliases_json + aliases))
            return entity

        entity = EntityORM(entity_type=entity_type, canonical_name=canonical_name, aliases_json=aliases or [])
        self.session.add(entity)
        self.session.flush()
        return entity

    def link_card_entity(self, card_id: int, entity_id: int, role: str, confidence: float) -> None:
        link = CardEntityORM(card_id=card_id, entity_id=entity_id, role=role, confidence=confidence)
        self.session.merge(link)

    def update_signal(self, entity_id: int, increment: float, metadata: dict | None = None) -> ContextSignalORM:
        signal = self.session.query(ContextSignalORM).filter(ContextSignalORM.entity_id == entity_id).one_or_none()
        now = datetime.utcnow()
        if not signal:
            signal = ContextSignalORM(
                entity_id=entity_id,
                strength=increment,
                mention_count=1,
                last_seen_at=now,
                metadata_json=metadata or {},
            )
            self.session.add(signal)
            return signal

        signal.strength = max(0.0, signal.strength * 0.95 + increment)
        signal.mention_count += 1
        signal.last_seen_at = now
        if metadata:
            signal.metadata_json = {**signal.metadata_json, **metadata}
        return signal

    def top_context_entities(self, limit: int = 10) -> list[ContextSignalORM]:
        return (
            self.session.query(ContextSignalORM)
            .order_by(ContextSignalORM.strength.desc(), ContextSignalORM.last_seen_at.desc())
            .limit(limit)
            .all()
        )
