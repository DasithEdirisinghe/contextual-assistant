from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CardType(str, Enum):
    TASK = "task"
    REMINDER = "reminder"
    IDEA_NOTE = "idea_note"


class ResolvedDate(BaseModel):
    original_text: Optional[str] = None
    resolved_at: Optional[datetime] = None
    timezone: str = "UTC"


class EntityMention(BaseModel):
    entity_type: str
    value: str
    role: str = "mentioned"
    confidence: float = 1.0


class ExtractedCard(BaseModel):
    card_type: CardType
    description: str = Field(min_length=1)
    date_text: Optional[str] = None
    assignee: Optional[str] = None
    context_keywords: list[str] = Field(default_factory=list)
    entities: list[EntityMention] = Field(default_factory=list)
    confidence: float = 0.0


class Card(BaseModel):
    id: int
    card_type: CardType
    description: str
    due_at: Optional[datetime]
    assignee: Optional[str]
    keywords: list[str]
    envelope_id: Optional[int]


class IngestResult(BaseModel):
    card: Card
    envelope_name: str
    match_score: float
    reason: str
    context_updates: list[str] = Field(default_factory=list)
