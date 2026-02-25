from __future__ import annotations

from sqlalchemy.orm import Session

from assistant.agents.context_agent import ContextAgent
from assistant.agents.ingestion_agent import IngestionAgent
from assistant.agents.organization_agent import OrganizationAgent
from assistant.agents.thinking_agent import ThinkingAgent
from assistant.config.settings import Settings
from assistant.db.repo_cards import CardsRepository
from assistant.db.repo_events import EventsRepository
from assistant.schemas.card import Card, IngestResult

INGESTION_SCHEMA_VERSION = "ingestion.schema.v4"


class AssistantOrchestrator:
    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings
        self.ingestion_agent = IngestionAgent(settings)
        self.organization_agent = OrganizationAgent(session, settings)
        self.cards_repo = CardsRepository(session)
        self.context_agent = ContextAgent()
        self.events_repo = EventsRepository(session)
        self.thinking_agent = ThinkingAgent(session, settings)

    def ingest_note(self, raw_text: str) -> IngestResult:
        try:
            extracted, model_name, prompt_version, latency_ms, success, error_text = self.ingestion_agent.extract(raw_text)
            decision, envelope_id = self.organization_agent.route(extracted)

            from assistant.services.datetime import parse_due_at

            card_orm = self.cards_repo.create_card(
                raw_text=raw_text,
                card_type=extracted.card_type.value,
                description=extracted.description,
                due_at=parse_due_at(extracted.date_text, timezone=self.settings.timezone),
                assignee_text=extracted.assignee,
                keywords=extracted.context_keywords,
                reasoning_steps=extracted.reasoning_steps,
                envelope_id=envelope_id,
            )

            context_updates = self.context_agent.update_from_card(card_orm.id, extracted)
            self.events_repo.log_ingestion(
                model_name=model_name,
                prompt_version=prompt_version,
                schema_version=INGESTION_SCHEMA_VERSION,
                success=success,
                latency_ms=latency_ms,
                card_id=card_orm.id,
                error_text=error_text,
            )
            self.session.commit()

            return IngestResult(
                card=Card(
                    id=card_orm.id,
                    card_type=extracted.card_type,
                    description=card_orm.description,
                    due_at=card_orm.due_at,
                    assignee=card_orm.assignee_text,
                    keywords=card_orm.keywords_json,
                    reasoning_steps=card_orm.reasoning_steps_json,
                    envelope_id=card_orm.envelope_id,
                ),
                envelope_name=decision.envelope_name,
                match_score=decision.score,
                reason=decision.reason,
                context_updates=context_updates,
            )
        except Exception:
            self.session.rollback()
            raise

    def run_thinking_cycle(self):
        return self.thinking_agent.run_cycle()
