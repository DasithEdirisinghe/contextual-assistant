from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


INGESTION_SCHEMA_VERSION = "ingestion.schema.v1"


class IngestionExtractedEntity(BaseModel):
    entity_type: Literal["person", "company", "project", "theme"]
    value: str = Field(min_length=1)
    role: Literal["assignee", "mentioned", "context"] = "mentioned"
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class IngestionExtractedCardSchema(BaseModel):
    card_type: Literal["task", "reminder", "idea_note"]
    description: str = Field(min_length=1)
    date_text: Optional[str] = None
    assignee: Optional[str] = None
    context_keywords: list[str] = Field(default_factory=list)
    entities: list[IngestionExtractedEntity] = Field(default_factory=list)
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)
