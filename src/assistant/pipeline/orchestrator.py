from __future__ import annotations

import logging
import re

from sqlalchemy.orm import Session

from assistant.agents.context.agent import ContextAgent
from assistant.agents.ingestion.agent import IngestionAgent
from assistant.agents.organization.agent import OrganizationAgent
from assistant.agents.thinking.agent import ThinkingAgent
from assistant.config.settings import Settings
from assistant.db.repo_cards import CardsRepository
from assistant.db.repo_events import EventsRepository
from assistant.prompts import resolve_prompt_version
from assistant.schemas.card import Card, IngestResult

INGESTION_SCHEMA_VERSION = "ingestion.schema.v4"
logger = logging.getLogger(__name__)


def _sanitize_db_url(url: str) -> str:
    # redact credentials if present: scheme://user:pass@host -> scheme://***:***@host
    return re.sub(r"://([^:/@]+):([^@]+)@", r"://***:***@", url)


class AssistantOrchestrator:
    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings
        resolved_ingestion_prompt = resolve_prompt_version("ingestion", settings.ingestion_prompt_version)
        logger.debug(
            "AssistantOrchestrator init: llm=%s/%s embedding=%s/%s db=%s ingestion_prompt=%s",
            settings.effective_llm_provider,
            settings.effective_llm_model,
            settings.effective_embedding_provider,
            settings.effective_embedding_model,
            _sanitize_db_url(settings.database_url),
            resolved_ingestion_prompt,
        )
        self.ingestion_agent = IngestionAgent(settings)
        self.organization_agent = OrganizationAgent(session, settings)
        self.cards_repo = CardsRepository(session)
        self.context_agent = ContextAgent(session, settings)
        self.events_repo = EventsRepository(session)
        self.thinking_agent = ThinkingAgent(session, settings)

    def ingest_note(self, raw_text: str) -> IngestResult:
        try:
            extracted, model_name, prompt_version, latency_ms, success, error_text = self.ingestion_agent.extract(raw_text)
            decision, envelope_id = self.organization_agent.route(extracted, raw_text)

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
            self.organization_agent.refresh_envelope(envelope_id)
            refreshed_envelope = self.organization_agent.envelopes.get_by_id(envelope_id)

            context_result = self.context_agent.update_context(card_orm.id)
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
                envelope_name=(refreshed_envelope.name if refreshed_envelope else decision.envelope_name),
                match_score=decision.score,
                reason=decision.reason,
                context_updates=context_result.messages,
            )
        except Exception:
            self.session.rollback()
            raise

    def run_thinking_cycle(self):
        return self.thinking_agent.run_cycle()
