from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from assistant.config.settings import Settings
from assistant.db.repo_cards import CardsRepository
from assistant.db.repo_context_snapshot import ContextSnapshotRepository
from assistant.db.repo_envelopes import EnvelopesRepository
from assistant.llm.client import build_chat_model
from assistant.prompts import load_prompt_versioned, resolve_prompt_version
from assistant.schemas.suggestion import ThinkingInputStats, ThinkingRunOutput, ThinkingSuggestionBatch

logger = logging.getLogger(__name__)


class ThinkingAgent:
    """LLM-first reasoning agent for proactive suggestions."""

    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings
        self.cards_repo = CardsRepository(session)
        self.envelopes_repo = EnvelopesRepository(session)
        self.context_repo = ContextSnapshotRepository(session)
        self.prompt_version = resolve_prompt_version("thinking", settings.thinking_prompt_version)
        logger.debug(
            "ThinkingAgent init: prompt_version=%s llm_provider=%s llm_model=%s max_cards=%s max_envelopes=%s",
            self.prompt_version,
            settings.effective_llm_provider,
            settings.effective_llm_model,
            settings.thinking_max_cards,
            settings.thinking_max_envelopes,
        )

    def _serialize_cards(self) -> list[dict]:
        cards = self.cards_repo.list_cards()[: max(1, self.settings.thinking_max_cards)]
        return [
            {
                "id": c.id,
                "card_type": c.card_type,
                "description": c.description,
                "due_at": c.due_at.isoformat() if c.due_at else None,
                "assignee": c.assignee_text,
                "keywords": c.keywords_json or [],
                "envelope_id": c.envelope_id,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in cards
        ]

    def _serialize_envelopes(self) -> list[dict]:
        envelopes = self.envelopes_repo.list_envelopes()[: max(1, self.settings.thinking_max_envelopes)]
        return [
            {
                "id": e.id,
                "name": e.name,
                "summary": e.summary,
                "keywords": e.keywords_json or [],
                "card_count": e.card_count,
                "last_card_at": e.last_card_at.isoformat() if e.last_card_at else None,
            }
            for e in envelopes
        ]

    def _serialize_context(self) -> dict:
        snapshot = self.context_repo.get_snapshot()
        if not snapshot:
            return {"context_json": {}, "focus_summary": None}

        try:
            parsed = json.loads(snapshot.context_json)
        except Exception:
            parsed = {}
        return {"context_json": parsed, "focus_summary": snapshot.focus_summary}

    def run_cycle(self) -> ThinkingRunOutput:
        cards = self._serialize_cards()
        envelopes = self._serialize_envelopes()
        user_context = self._serialize_context()
        input_stats = ThinkingInputStats(cards_scanned=len(cards), envelopes_scanned=len(envelopes))

        prompt = load_prompt_versioned(
            "thinking",
            version=self.prompt_version,
            cards_json=json.dumps(cards, ensure_ascii=False, indent=2),
            envelopes_json=json.dumps(envelopes, ensure_ascii=False, indent=2),
            user_context_json=json.dumps(user_context, ensure_ascii=False, indent=2),
        )
        llm = build_chat_model(self.settings)
        logger.debug(
            "ThinkingAgent run_cycle: prompt_version=%s cards=%s envelopes=%s",
            self.prompt_version,
            len(cards),
            len(envelopes),
        )
        parsed = llm.with_structured_output(ThinkingSuggestionBatch).invoke(prompt)
        batch = ThinkingSuggestionBatch.model_validate(parsed)

        return ThinkingRunOutput(
            run_id=f"thinking-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}",
            generated_at=datetime.now(timezone.utc),
            model_name=f"{self.settings.effective_llm_provider}:{self.settings.effective_llm_model}",
            prompt_version=self.prompt_version,
            input_stats=input_stats,
            suggestions=batch.suggestions,
        )
