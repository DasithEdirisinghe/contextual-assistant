from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from assistant.config.settings import Settings
from assistant.db.repo_context_snapshot import ContextSnapshotRepository
from assistant.schemas.context import ContextUpdateOutput, StructuredUserContext
from assistant.agents.context.evidence import build_context_evidence
from assistant.agents.context.updater import ContextUpdateError, ContextUpdater


@dataclass
class ContextUpdateResult:
    updated: bool
    evidence_count: int
    messages: list[str]


class ContextAgent:
    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings
        self.snapshot_repo = ContextSnapshotRepository(session)
        self.updater = ContextUpdater(settings)

    @staticmethod
    def _default_context_json() -> str:
        empty = StructuredUserContext().model_dump(mode="json")
        return json.dumps(empty, ensure_ascii=False)

    def update_context(self, card_id: int) -> ContextUpdateResult:
        snapshot = self.snapshot_repo.get_snapshot()
        previous_context_json = snapshot.context_json if snapshot else self._default_context_json()
        evidence = build_context_evidence(self.session, max_cards=12)
        if not evidence:
            return ContextUpdateResult(updated=False, evidence_count=0, messages=["context unchanged: no evidence"])

        try:
            updated_output = self.updater.update(previous_context_json=previous_context_json, evidence=evidence)
            now = datetime.utcnow()
            self.snapshot_repo.upsert_snapshot(
                context_json=updated_output.context.model_dump_json(),
                focus_summary=updated_output.focus_summary,
                updated_at=now,
            )
            return ContextUpdateResult(
                updated=True,
                evidence_count=len(evidence),
                messages=[f"context updated with {len(evidence)} evidence cards"],
            )
        except ContextUpdateError:
            # keep previous snapshot unchanged
            return ContextUpdateResult(
                updated=False,
                evidence_count=len(evidence),
                messages=["context unchanged: llm update failed, previous snapshot kept"],
            )
