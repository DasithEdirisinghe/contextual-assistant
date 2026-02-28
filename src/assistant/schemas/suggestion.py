from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class SuggestionType(str, Enum):
    CONFLICT = "conflict"
    NEXT_STEP = "next_step"
    RECOMMENDATION = "recommendation"


class SuggestionPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ThinkingEvidence(BaseModel):
    card_ids: list[int] = Field(default_factory=list)
    envelope_ids: list[int] = Field(default_factory=list)
    context_keys: list[str] = Field(default_factory=list)


class ThinkingSuggestionItem(BaseModel):
    suggestion_type: SuggestionType
    title: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)
    priority: SuggestionPriority
    score: float = Field(ge=0.0, le=1.0)
    reasoning_steps: list[str] = Field(default_factory=list, min_length=1)
    evidence: ThinkingEvidence = Field(default_factory=ThinkingEvidence)


class ThinkingInputStats(BaseModel):
    cards_scanned: int = 0
    envelopes_scanned: int = 0


class ThinkingRunOutput(BaseModel):
    run_id: str
    generated_at: datetime
    model_name: str
    prompt_version: str
    input_stats: ThinkingInputStats
    suggestions: list[ThinkingSuggestionItem] = Field(default_factory=list)


class ThinkingSuggestionBatch(BaseModel):
    suggestions: list[ThinkingSuggestionItem] = Field(default_factory=list)


class ThinkingArtifactRecord(BaseModel):
    artifact_path: str
    run_id: str
    generated_at: datetime
    suggestions_count: int
    by_type: dict[Literal["conflict", "next_step", "recommendation"], int] = Field(default_factory=dict)
