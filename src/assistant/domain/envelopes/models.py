from pydantic import BaseModel


class EnvelopeDecision(BaseModel):
    action: str
    envelope_id: int | None = None
    envelope_name: str
    score: float
    reason: str
