from typing import Literal

from pydantic import BaseModel, Field


SCHEMA_VERSION = "v1"


class ExtractedEntity(BaseModel):
    entity_type: Literal["person", "company", "project", "theme"]
    value: str = Field(min_length=1)
    role: Literal["assignee", "mentioned", "context"] = "mentioned"
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class ExtractedCardSchema(BaseModel):
    card_type: Literal["task", "reminder", "idea_note"]
    description: str = Field(min_length=1)
    date_text: str | None = None
    assignee: str | None = None
    context_keywords: list[str] = Field(default_factory=list)
    entities: list[ExtractedEntity] = Field(default_factory=list)
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)
