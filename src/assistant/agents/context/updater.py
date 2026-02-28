from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from assistant.config.settings import Settings
from assistant.llm.client import build_chat_model
from assistant.prompts import load_prompt_versioned, resolve_prompt_version
from assistant.schemas.context import ContextUpdateOutput
from assistant.agents.context.evidence import ContextEvidenceCard

logger = logging.getLogger(__name__)


class ContextUpdateError(RuntimeError):
    pass


def _format_evidence(evidence: list[ContextEvidenceCard]) -> str:
    rows = []
    for c in evidence:
        rows.append(
            {
                "card_id": c.card_id,
                "card_type": c.card_type,
                "description": c.description,
                "assignee": c.assignee,
                "keywords": c.keywords,
                "due_at": c.due_at.isoformat() if c.due_at else None,
                "envelope_id": c.envelope_id,
                "envelope_name": c.envelope_name,
                "created_at": c.created_at.isoformat(),
            }
        )
    return json.dumps(rows, ensure_ascii=False, indent=2)


class ContextUpdater:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.prompt_version = resolve_prompt_version("context_update", settings.context_update_prompt_version)
        logger.debug(
            "ContextUpdater init: prompt_version=%s llm_provider=%s llm_model=%s",
            self.prompt_version,
            self.settings.effective_llm_provider,
            self.settings.effective_llm_model,
        )

    def _llm_enabled(self) -> bool:
        provider = self.settings.effective_llm_provider
        if provider in {"openai", "deepseek", "openai_compatible"} and not self.settings.effective_llm_api_key:
            return False
        return True

    def update(self, previous_context_json: str, evidence: list[ContextEvidenceCard]) -> ContextUpdateOutput:
        if not self._llm_enabled():
            raise ContextUpdateError("LLM unavailable for context update")
        if not evidence:
            raise ContextUpdateError("No evidence cards available for context update")

        system_prompt = load_prompt_versioned(
            "context_update",
            version=self.prompt_version,
        )
        human_payload = (
            f"Previous context JSON:\n{previous_context_json}\n\n"
            f"Evidence cards JSON:\n{_format_evidence(evidence)}"
        )
        try:
            llm = build_chat_model(self.settings)
            logger.debug(
                "ContextUpdater update: prompt_version=%s evidence_count=%s human_payload_len=%s",
                self.prompt_version,
                len(evidence),
                len(human_payload),
            )
            result = llm.with_structured_output(ContextUpdateOutput).invoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=human_payload)]
            )
            return ContextUpdateOutput.model_validate(result)
        except Exception as exc:  # noqa: BLE001
            raise ContextUpdateError(str(exc)) from exc
