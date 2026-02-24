from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SuggestionType(str, Enum):
    CONFLICT = "conflict"
    NEXT_STEP = "next_step"
    RECOMMENDATION = "recommendation"


class Suggestion(BaseModel):
    suggestion_type: SuggestionType
    title: str
    message: str
    priority: str
    score: float
    related_refs: dict = Field(default_factory=dict)
    fingerprint: str


class ThinkingRunSummary(BaseModel):
    run_id: int
    cards_scanned: int
    envelopes_scanned: int
    candidates: int
    created: int
    dedup_skipped: int
    by_type: dict[str, int]
    duration_ms: int
