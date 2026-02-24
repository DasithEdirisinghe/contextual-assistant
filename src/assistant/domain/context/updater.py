from assistant.domain.cards.models import ExtractedCard
from assistant.ml.normalization.entity_normalizer import canonicalize_entity
from assistant.persistence.repositories.context_repo import ContextRepository


class ContextUpdater:
    def __init__(self, repo: ContextRepository):
        self.repo = repo

    def update_from_card(self, card_id: int, extracted: ExtractedCard) -> list[str]:
        updates: list[str] = []

        for entity in extracted.entities:
            canonical = canonicalize_entity(entity.value)
            orm_entity = self.repo.upsert_entity(entity.entity_type, canonical, aliases=[entity.value])
            self.repo.link_card_entity(card_id, orm_entity.id, entity.role, entity.confidence)
            self.repo.update_signal(
                orm_entity.id,
                increment=max(0.2, entity.confidence),
                metadata={"source": "ingestion"},
            )
            updates.append(f"{entity.entity_type}:{canonical}")

        if extracted.assignee:
            canonical = canonicalize_entity(extracted.assignee)
            person = self.repo.upsert_entity("person", canonical, aliases=[extracted.assignee])
            self.repo.link_card_entity(card_id, person.id, "assignee", 0.8)
            self.repo.update_signal(person.id, increment=0.9, metadata={"role": "assignee"})
            updates.append(f"person:{canonical}")

        for keyword in extracted.context_keywords[:5]:
            theme = self.repo.upsert_entity("theme", canonicalize_entity(keyword))
            self.repo.link_card_entity(card_id, theme.id, "context", 0.6)
            self.repo.update_signal(theme.id, increment=0.4, metadata={"role": "theme"})
            updates.append(f"theme:{theme.canonical_name}")

        return updates
