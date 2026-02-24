from sqlalchemy.orm import Session

from assistant.config.settings import Settings
from assistant.domain.cards.enums import CardType
from assistant.domain.cards.models import CardRecord, IngestResult
from assistant.domain.cards.service import CardExtractionService
from assistant.domain.context.updater import ContextUpdater
from assistant.domain.envelopes.matcher import EnvelopeMatcher
from assistant.ml.extraction.prompts import PROMPT_VERSION
from assistant.ml.extraction.schemas import SCHEMA_VERSION
from assistant.ml.normalization.time_parser import parse_due_at
from assistant.persistence.repositories.cards_repo import CardsRepository
from assistant.persistence.repositories.context_repo import ContextRepository
from assistant.persistence.repositories.envelopes_repo import EnvelopesRepository
from assistant.persistence.repositories.events_repo import EventsRepository


class IngestionAgent:
    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings
        self.cards_repo = CardsRepository(session)
        self.env_repo = EnvelopesRepository(session)
        self.context_repo = ContextRepository(session)
        self.events_repo = EventsRepository(session)
        self.extractor = CardExtractionService(settings)
        self.matcher = EnvelopeMatcher(settings)

    def ingest(self, raw_text: str) -> IngestResult:
        extracted, model_name, latency_ms, success, error_text = self.extractor.extract(raw_text)
        due_at = parse_due_at(extracted.date_text, timezone=self.settings.timezone)

        envelopes = self.env_repo.list_envelopes()
        entity_values = [e.value.lower() for e in extracted.entities]
        match = self.matcher.choose_best(extracted.description, extracted.context_keywords, entity_values, envelopes)

        envelope = match.envelope
        reason = match.reason
        score = match.score
        if envelope is None or score < self.settings.envelope_assign_threshold:
            base_name = extracted.context_keywords[0] if extracted.context_keywords else extracted.card_type
            envelope_name = base_name.replace("_", " ").title()
            existing = self.env_repo.get_by_name(envelope_name)
            envelope = existing or self.env_repo.create_envelope(envelope_name, summary=extracted.description[:180])
            reason = f"created new envelope (score={score:.2f})"

        card = self.cards_repo.create_card(
            raw_text=raw_text,
            card_type=extracted.card_type,
            description=extracted.description,
            due_at=due_at,
            assignee_text=extracted.assignee,
            keywords=extracted.context_keywords,
            envelope_id=envelope.id,
        )

        updater = ContextUpdater(self.context_repo)
        updates = updater.update_from_card(card.id, extracted)

        self.events_repo.log_ingestion(
            model_name=model_name,
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
            success=success,
            latency_ms=latency_ms,
            card_id=card.id,
            error_text=error_text,
        )

        self.session.commit()

        record = CardRecord(
            id=card.id,
            card_type=CardType(card.card_type),
            description=card.description,
            due_at=card.due_at,
            assignee=card.assignee_text,
            keywords=card.keywords_json,
            envelope_id=card.envelope_id,
        )
        return IngestResult(
            card=record,
            envelope_name=envelope.name,
            match_score=score,
            reason=reason,
            context_updates=updates,
        )
