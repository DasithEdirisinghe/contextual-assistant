from sqlalchemy.orm import Session

from assistant.persistence.models import ThinkingRunORM, ThinkingSuggestionORM


class ThinkingRepository:
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

    def list_suggestions(self) -> list[ThinkingSuggestionORM]:
        return self.session.query(ThinkingSuggestionORM).order_by(ThinkingSuggestionORM.created_at.desc()).all()
