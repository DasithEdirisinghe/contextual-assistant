from __future__ import annotations

import re

from assistant.schemas.card import ExtractedCard


def _canonicalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).title()


class ContextAgent:
    """Deterministic updater that derives context tags from card fields."""

    def update_from_card(self, card_id: int, extracted: ExtractedCard) -> list[str]:
        updates: list[str] = []
        if extracted.assignee:
            canonical = _canonicalize(extracted.assignee)
            updates.append(f"person:{canonical}")

        for keyword in extracted.context_keywords[:5]:
            updates.append(f"theme:{_canonicalize(keyword)}")

        return updates
