from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from assistant.agents.thinking.rules import build_thinking_candidates
from assistant.config.settings import Settings
from assistant.db.repo_cards import CardsRepository
from assistant.db.repo_envelopes import EnvelopesRepository
from assistant.db.repo_suggestions import SuggestionsRepository
from assistant.schemas.suggestion import ThinkingRunSummary

logger = logging.getLogger(__name__)


class ThinkingAgent:
    """Batch reasoning agent for proactive suggestions."""

    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings
        self.cards_repo = CardsRepository(session)
        self.envelopes_repo = EnvelopesRepository(session)
        self.suggestions_repo = SuggestionsRepository(session)

    def run_cycle(self) -> ThinkingRunSummary:
        started = datetime.utcnow()
        run = self.suggestions_repo.create_run(status="started")

        try:
            cards = self.cards_repo.list_cards()
            envelopes = self.envelopes_repo.list_envelopes()
            candidates = build_thinking_candidates(cards, envelopes)

            created = 0
            skipped = 0
            by_type: dict[str, int] = {"conflict": 0, "next_step": 0, "recommendation": 0}

            for candidate in candidates:
                if self.suggestions_repo.find_open_by_fingerprint(candidate.fingerprint):
                    skipped += 1
                    continue

                self.suggestions_repo.add_suggestion(
                    run_id=run.id,
                    suggestion_type=candidate.suggestion_type,
                    title=candidate.title,
                    message=candidate.message,
                    priority=candidate.priority,
                    score=candidate.score,
                    related_refs=candidate.related_refs,
                    fingerprint=candidate.fingerprint,
                )
                by_type[candidate.suggestion_type] = by_type.get(candidate.suggestion_type, 0) + 1
                created += 1

            summary = ThinkingRunSummary(
                run_id=run.id,
                cards_scanned=len(cards),
                envelopes_scanned=len(envelopes),
                candidates=len(candidates),
                created=created,
                dedup_skipped=skipped,
                by_type=by_type,
                duration_ms=int((datetime.utcnow() - started).total_seconds() * 1000),
            )
            self.suggestions_repo.complete_run(run.id, summary.model_dump())
            self.session.commit()
            return summary
        except Exception as exc:  # noqa: BLE001
            logger.exception("Thinking run failed")
            self.suggestions_repo.fail_run(run.id, str(exc))
            self.session.commit()
            raise
