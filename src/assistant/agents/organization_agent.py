from __future__ import annotations

from sqlalchemy.orm import Session

from assistant.config.settings import Settings
from assistant.db.repo_envelopes import EnvelopesRepository
from assistant.schemas.card import ExtractedCard
from assistant.schemas.envelope import EnvelopeDecision
from assistant.services.scoring import EnvelopeScorer


class OrganizationAgent:
    """Deterministic routing: choose/create envelope for a card."""

    def __init__(self, session: Session, settings: Settings):
        self.settings = settings
        self.envelopes = EnvelopesRepository(session)
        self.scorer = EnvelopeScorer(settings)

    def route(self, extracted: ExtractedCard) -> tuple[EnvelopeDecision, int]:
        all_envelopes = self.envelopes.list_envelopes()
        match = self.scorer.choose_best(extracted.description, extracted.context_keywords, all_envelopes)

        envelope = match.envelope
        if envelope is None or match.score < self.settings.envelope_assign_threshold:
            base_name = extracted.context_keywords[0] if extracted.context_keywords else extracted.card_type.value
            envelope_name = base_name.replace("_", " ").title()
            existing = self.envelopes.get_by_name(envelope_name)
            envelope = existing or self.envelopes.create_envelope(envelope_name, summary=extracted.description[:180])
            decision = EnvelopeDecision(
                action="create_or_assign",
                envelope_id=envelope.id,
                envelope_name=envelope.name,
                score=match.score,
                reason=f"created new envelope (score={match.score:.2f})",
            )
            return decision, envelope.id

        decision = EnvelopeDecision(
            action="assign",
            envelope_id=envelope.id,
            envelope_name=envelope.name,
            score=match.score,
            reason=match.reason,
        )
        return decision, envelope.id
