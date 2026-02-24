from __future__ import annotations

import re

from assistant.db.repo_context import ContextRepository
from assistant.schemas.card import ExtractedCard


def _canonicalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).title()


class ContextAgent:
    """Deterministic updater for context/entity signals."""

    def __init__(self, repo: ContextRepository):
        self.repo = repo

    def update_from_card(self, card_id: int, extracted: ExtractedCard) -> list[str]:
        updates: list[str] = []

        for entity in extracted.entities:
            canonical = _canonicalize(entity.value)
            orm_entity = self.repo.upsert_entity(entity.entity_type, canonical, aliases=[entity.value])
            self.repo.link_card_entity(card_id, orm_entity.id, entity.role, entity.confidence)
            self.repo.update_signal(orm_entity.id, increment=max(0.2, entity.confidence), metadata={"source": "ingestion"})
            updates.append(f"{entity.entity_type}:{canonical}")

        assignee_already_linked = any(
            e.entity_type == "person"
            and e.role == "assignee"
            and _canonicalize(e.value) == _canonicalize(extracted.assignee or "")
            for e in extracted.entities
        )
        if extracted.assignee and not assignee_already_linked:
            canonical = _canonicalize(extracted.assignee)
            person = self.repo.upsert_entity("person", canonical, aliases=[extracted.assignee])
            self.repo.link_card_entity(card_id, person.id, "assignee", 0.8)
            self.repo.update_signal(person.id, increment=0.9, metadata={"role": "assignee"})
            updates.append(f"person:{canonical}")

        for keyword in extracted.context_keywords[:5]:
            theme = self.repo.upsert_entity("theme", _canonicalize(keyword))
            self.repo.link_card_entity(card_id, theme.id, "context", 0.6)
            self.repo.update_signal(theme.id, increment=0.4, metadata={"role": "theme"})
            updates.append(f"theme:{theme.canonical_name}")

        return updates
