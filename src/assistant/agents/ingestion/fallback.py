import re

from assistant.schemas.card import EntityMention, ExtractedCard
from assistant.services.keywords import extract_keywords

TASK_VERBS = {
    "call",
    "send",
    "prepare",
    "finish",
    "book",
    "review",
    "write",
    "plan",
    "schedule",
    "follow",
}


class FallbackExtractor:
    def extract(self, raw_text: str) -> ExtractedCard:
        text = raw_text.strip()
        lower = text.lower()

        date_text = None
        for marker in ["tomorrow", "next monday", "next tuesday", "next week", "today", "tonight"]:
            if marker in lower:
                date_text = marker
                break

        keywords = extract_keywords(text, limit=8)

        card_type = "idea_note"
        if any(word in lower for word in ["remember", "remind", "pick up", "dont forget", "don't forget"]) or date_text:
            card_type = "reminder"
        if any(lower.startswith(v + " ") or f" {v} " in lower for v in TASK_VERBS):
            card_type = "task"

        assignee = None
        entities: list[EntityMention] = []
        name_match = re.search(
            r"\b(?:with|to)\s+([A-Z][a-z]+)\b|\b(?:[Cc]all|[Ee]mail|[Mm]essage|[Pp]ing|[Mm]eet)\s+([A-Z][a-z]+)\b",
            text,
        )
        if name_match:
            assignee = next(group for group in name_match.groups() if group)
            entities.append(EntityMention(entity_type="person", value=assignee, role="assignee", confidence=0.6))

        return ExtractedCard(
            card_type=card_type,
            description=text,
            date_text=date_text,
            assignee=assignee,
            context_keywords=sorted(set(keywords[:6])),
            entities=entities,
            confidence=0.55,
        )
