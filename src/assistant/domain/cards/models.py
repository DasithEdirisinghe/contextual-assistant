from datetime import datetime

from pydantic import BaseModel, Field

from assistant.domain.cards.enums import CardType


class EntityMention(BaseModel):
    entity_type: str
    value: str
    role: str = "mentioned"
    confidence: float = 1.0


class ExtractedCard(BaseModel):
    card_type: CardType
    description: str = Field(min_length=1)
    date_text: str | None = None
    assignee: str | None = None
    context_keywords: list[str] = Field(default_factory=list)
    entities: list[EntityMention] = Field(default_factory=list)
    confidence: float = 0.0


class CardRecord(BaseModel):
    id: int
    card_type: CardType
    description: str
    due_at: datetime | None
    assignee: str | None
    keywords: list[str]
    envelope_id: int | None


class IngestResult(BaseModel):
    card: CardRecord
    envelope_name: str
    match_score: float
    reason: str
    context_updates: list[str] = Field(default_factory=list)
