# System Architecture

## Components
- CLI (`Typer`) for note ingestion and inspection.
- Ingestion & Organization Agent for extraction, normalization, routing, persistence.
- Context manager for dynamic user context updates.
- SQLite persistence layer with 8-table schema.
- Thinking Agent design contract for scheduled proactive suggestions.

## High-Level Data Flow
1. User submits raw note in CLI.
2. Extractor returns structured card fields under Pydantic schema.
3. Date parser normalizes relative dates.
4. Envelope matcher computes hybrid similarity and assigns/creates envelope.
5. Card and linked entities are persisted.
6. Context signals are updated with recency-aware strength.
7. Ingestion telemetry event is written for observability.
