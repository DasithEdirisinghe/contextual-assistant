from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Envelope(BaseModel):
    id: int
    name: str
    summary: Optional[str] = None


class EnvelopeDecision(BaseModel):
    action: str
    envelope_id: Optional[int] = None
    envelope_name: str
    score: float
    reason: str
