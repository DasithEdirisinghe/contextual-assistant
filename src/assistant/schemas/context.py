from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ContextItem(BaseModel):
    name: str
    strength: float
    evidence_card_ids: list[int] = Field(default_factory=list)
    last_seen_at: Optional[datetime] = None


class ImportantUpcomingItem(BaseModel):
    card_id: int
    title: str
    reason: str


class StructuredUserContext(BaseModel):
    people: list[ContextItem] = Field(default_factory=list)
    organizations: list[ContextItem] = Field(default_factory=list)
    projects: list[ContextItem] = Field(default_factory=list)
    themes: list[ContextItem] = Field(default_factory=list)
    important_upcoming: list[ImportantUpcomingItem] = Field(default_factory=list)
    miscellaneous: list[ContextItem] = Field(default_factory=list)


class ContextUpdateOutput(BaseModel):
    context: StructuredUserContext
    focus_summary: str
