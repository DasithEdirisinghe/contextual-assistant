from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from assistant.db.models import ThinkingRunORM, ThinkingSuggestionORM


class SuggestionsRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_run(self, status: str = "started") -> ThinkingRunORM:
        run = ThinkingRunORM(status=status)
        self.session.add(run)
        self.session.flush()
        return run

    def add_suggestion(
        self,
        run_id: int | None,
        suggestion_type: str,
        title: str,
        message: str,
        priority: str,
        score: float,
        related_refs: dict,
        fingerprint: str,
    ) -> ThinkingSuggestionORM:
        suggestion = ThinkingSuggestionORM(
            run_id=run_id,
            suggestion_type=suggestion_type,
            title=title,
            message=message,
            priority=priority,
            score=score,
            related_refs_json=related_refs,
            fingerprint=fingerprint,
        )
        self.session.add(suggestion)
        self.session.flush()
        return suggestion

    def find_open_by_fingerprint(self, fingerprint: str) -> Optional[ThinkingSuggestionORM]:
        return (
            self.session.query(ThinkingSuggestionORM)
            .filter(ThinkingSuggestionORM.fingerprint == fingerprint, ThinkingSuggestionORM.status == "open")
            .one_or_none()
        )

    def complete_run(self, run_id: int, summary_json: dict) -> None:
        run = self.session.query(ThinkingRunORM).filter(ThinkingRunORM.id == run_id).one()
        run.status = "completed"
        run.summary_json = summary_json
        run.completed_at = datetime.utcnow()

    def fail_run(self, run_id: int, error_text: str) -> None:
        run = self.session.query(ThinkingRunORM).filter(ThinkingRunORM.id == run_id).one()
        run.status = "failed"
        run.summary_json = {"error": error_text}
        run.completed_at = datetime.utcnow()

    def list_suggestions(self, status: Optional[str] = None, limit: int = 50) -> list[ThinkingSuggestionORM]:
        query = self.session.query(ThinkingSuggestionORM)
        if status:
            query = query.filter(ThinkingSuggestionORM.status == status)
        return query.order_by(ThinkingSuggestionORM.created_at.desc()).limit(limit).all()
