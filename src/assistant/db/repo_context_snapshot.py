from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from assistant.db.models import UserContextORM


class ContextSnapshotRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_snapshot(self) -> UserContextORM | None:
        return self.session.query(UserContextORM).filter(UserContextORM.id == 1).one_or_none()

    def upsert_snapshot(self, *, context_json: str, focus_summary: str | None, updated_at: datetime) -> UserContextORM:
        row = self.get_snapshot()
        if row is None:
            row = UserContextORM(id=1, context_json=context_json, focus_summary=focus_summary, updated_at=updated_at)
            self.session.add(row)
        else:
            row.context_json = context_json
            row.focus_summary = focus_summary
            row.updated_at = updated_at
        self.session.flush()
        return row
