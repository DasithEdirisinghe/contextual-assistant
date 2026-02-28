from __future__ import annotations

from sqlalchemy.orm import Session

from assistant.config.settings import Settings
from assistant.db.repo_cards import CardsRepository
from assistant.db.repo_envelopes import EnvelopesRepository
from assistant.schemas.card import ExtractedCard
from assistant.schemas.envelope import EnvelopeDecision
from assistant.agents.organization.profile import build_envelope_profile
from assistant.agents.organization.refiner import EnvelopeRefiner
from assistant.services.embeddings import model_embed
from assistant.services.scoring import EnvelopeScorer


class OrganizationAgent:
    """Deterministic routing: choose/create envelope for a card."""

    def __init__(self, session: Session, settings: Settings):
        self.settings = settings
        self.envelopes = EnvelopesRepository(session)
        self.cards = CardsRepository(session)
        self.scorer = EnvelopeScorer(settings)
        self.refiner = EnvelopeRefiner(settings)

    def route(self, extracted: ExtractedCard, raw_text: str) -> tuple[EnvelopeDecision, int]:
        all_envelopes = self.envelopes.list_envelopes()
        card_embedding = model_embed(raw_text, settings=self.settings)
        match = self.scorer.choose_best(
            raw_text,
            extracted.context_keywords,
            all_envelopes,
            card_embedding=card_embedding,
            assignee=extracted.assignee,
        )

        envelope = match.envelope
        if envelope is None or match.score < self.settings.envelope_assign_threshold:
            base_name = extracted.context_keywords[0] if extracted.context_keywords else extracted.card_type.value
            envelope_name = base_name.replace("_", " ").title()
            existing = self.envelopes.get_by_name(envelope_name)
            envelope = existing or self.envelopes.create_envelope(envelope_name, summary=extracted.description[:180])
            decision = EnvelopeDecision(
                action="create",
                envelope_id=envelope.id,
                envelope_name=envelope.name,
                score=match.score,
                reason=f"created new envelope since threshold({self.settings.envelope_assign_threshold:.2f}) not met (score={match.score:.2f} with best matching envelope={match.envelope.name if match.envelope else 'none'})",
            )
            return decision, envelope.id

        decision = EnvelopeDecision(
            action="assign",
            envelope_id=envelope.id,
            envelope_name=envelope.name,
            score=match.score,
            reason=f"assigned to existing envelope since threshold({self.settings.envelope_assign_threshold:.2f}) met (score={match.score:.2f} with best matching envelope={match.envelope.name})",
        )
        return decision, envelope.id

    def refresh_envelope(self, envelope_id: int) -> None:
        envelope = self.envelopes.get_by_id(envelope_id)
        if envelope is None:
            return
        cards = self.cards.list_by_envelope(envelope_id)
        profile = build_envelope_profile(cards, settings=self.settings)
        self.envelopes.update_profile(
            envelope,
            keywords=profile.keywords,
            embedding_vector=profile.embedding_vector,
            card_count=profile.card_count,
            last_card_at=profile.last_card_at,
        )
        refined = self.refiner.refine(envelope, cards)
        self.envelopes.update_summary(envelope, name=refined.name, summary=refined.summary)
