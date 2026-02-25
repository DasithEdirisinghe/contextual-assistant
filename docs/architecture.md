# System Architecture

## Components
- CLI (`Typer`) for ingestion and inspection.
- Pipeline orchestrator (`assistant.pipeline.orchestrator`) coordinates deterministic execution order.
- Agent layer:
  - `IngestionAgent`: extract structured card
  - `OrganizationAgent`: route/create envelope
  - `ContextAgent`: derive context tags from card fields
  - `ThinkingAgent`: batch proactive suggestions
- Prompt assets loaded from external templates in `assistant/prompts/*.jinja`.
- Shared LLM runtime in `assistant.llm`.
- Utility services in `assistant.services`.
- DB access in `assistant.db` repositories over SQLAlchemy models.

## High-Level Data Flow
1. User submits a raw note via CLI.
2. `IngestionAgent` returns structured extraction.
3. `OrganizationAgent` scores and decides envelope assignment/creation.
4. Card is persisted.
5. `ContextAgent` derives context tags from assignee and keywords.
6. Ingestion event metadata is logged.
7. `ThinkingAgent` can run scheduled cycles to persist proactive suggestions.
