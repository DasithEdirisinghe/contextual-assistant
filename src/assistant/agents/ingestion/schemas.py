from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


INGESTION_SCHEMA_VERSION = "ingestion.schema.v4"


class IngestionExtractedCardSchema(BaseModel):
    card_type: Literal["task", "reminder", "idea_note"]
    description: str = Field(min_length=1)
    date_text: Optional[str] = None
    assignee: Optional[str] = None
    context_keywords: list[str] = Field(default_factory=list)
    reasoning_steps: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)
