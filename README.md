# Contextual Personal Assistant (Prototype)

Python prototype for the assignment: transform unstructured notes into structured cards, auto-organize them into envelopes, and maintain dynamic user context.

## Tech Choices
- Agent orchestration: lightweight modular Python services (LangChain-ready design).
- Structured extraction: OpenAI + `instructor` + Pydantic schema (single-call extraction).
- Fallback extraction: deterministic local rules (no API key mode).
- Storage: SQLite + SQLAlchemy.
- Interface: Typer CLI.

## Why this architecture
- Keeps the system simple and maintainable while preserving depth on core ingestion quality.
- Uses typed interfaces and strict schema validation to avoid brittle parsing.
- Supports future scaling through clean boundaries: extraction, matching, context, persistence, orchestration.

## Project Structure
- `src/assistant/interfaces/cli/app.py`: CLI commands
- `src/assistant/orchestration/ingestion_agent.py`: ingestion pipeline coordinator
- `src/assistant/ml/extraction/*`: prompt/schema/LLM/fallback extraction
- `src/assistant/domain/envelopes/matcher.py`: hybrid envelope matching
- `src/assistant/domain/context/updater.py`: dynamic context refinement
- `src/assistant/persistence/models.py`: SQLite schema (8 tables)
- `docs/thinking-agent-design.md`: scheduled Thinking Agent design

## Setup
1. Create a virtual env and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
```

Optional for high-quality extraction:
- Set `OPENAI_API_KEY` in `.env`.
- Without key, fallback extractor is used.

## Run
### Ingest a note
```bash
PYTHONPATH=src python -m assistant.interfaces.cli.app ingest "Call Sarah about the Q3 budget next Monday"
```

### View cards
```bash
PYTHONPATH=src python -m assistant.interfaces.cli.app cards-list
```

### View envelopes
```bash
PYTHONPATH=src python -m assistant.interfaces.cli.app envelopes-list
PYTHONPATH=src python -m assistant.interfaces.cli.app envelope-show 1
```

### View context
```bash
PYTHONPATH=src python -m assistant.interfaces.cli.app context-show
```

### Thinking Agent sample output (design-only)
```bash
PYTHONPATH=src python -m assistant.interfaces.cli.app thinking-sample
```

## Ingestion Agent Flow
1. Accept raw note.
2. Extract structured fields via schema-constrained LLM call (or fallback).
3. Normalize date/time (`dateparser`).
4. Score against existing envelopes using hybrid similarity:
   - keyword overlap
   - entity overlap
   - semantic similarity
5. Assign to best envelope or create a new envelope.
6. Persist card + entities + context signals.
7. Log ingestion event metadata for observability.

## Database Schema (8 tables)
- `cards`
- `envelopes`
- `entities`
- `card_entities`
- `context_signals`
- `thinking_runs`
- `thinking_suggestions`
- `ingestion_events`

## Thinking Agent Design (not implemented)
The designed Thinking Agent runs hourly and writes persistent suggestions using `thinking_runs` and `thinking_suggestions`:
- Next-step suggestion
- Recommendation (cluster related ideas)
- Conflict detection (assignee/date overlap)

See `docs/thinking-agent-design.md` for full logic flow.

## Testing
Run:
```bash
PYTHONPATH=src pytest -q
```

Included tests:
- date normalization
- fallback extraction
- envelope matching
- end-to-end ingestion with SQLite in-memory DB
