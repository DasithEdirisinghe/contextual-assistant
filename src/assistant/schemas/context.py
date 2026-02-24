from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ContextSignal(BaseModel):
    entity_type: str
    canonical_name: str
    strength: float
    mention_count: int
    last_seen_at: Optional[datetime] = None


class UserContext(BaseModel):
    signals: list[ContextSignal] = Field(default_factory=list)
