# Contextual Personal Assistant (Prototype)

Python prototype that transforms unstructured notes into structured cards, routes them into envelopes, updates user context, and generates proactive thinking suggestions.

## Tech Choices
- Orchestration: explicit pipeline orchestrator (`assistant.pipeline.orchestrator`)
- LLM extraction: LangChain + Pydantic structured parsing
- LLM providers: `openai`, `deepseek`, `ollama`, `openai_compatible`
- Fallback extraction: deterministic local rules
- Storage: SQLite + SQLAlchemy
- Interface: Typer CLI

## Project Structure
- `src/assistant/schemas/*`: centralized Pydantic contracts
- `src/assistant/prompts/*.jinja`: external prompt templates + loader
- `src/assistant/prompts/registry.yaml`: prompt snapshot/version registry
- `src/assistant/llm/client.py`: provider client factory
- `src/assistant/llm/parsing.py`: structured parse helpers
- `src/assistant/services/*`: datetime/keywords/embeddings/scoring utilities
- `src/assistant/db/*`: DB connection and repositories
- `src/assistant/agents/ingestion|organization|context|thinking/*`: agent implementations
- `src/assistant/pipeline/orchestrator.py`: end-to-end orchestration
- `src/assistant/interfaces/cli/app.py`: CLI commands
- `scripts/init_db.py`, `scripts/run_thinking.py`, `scripts/demo_ingest.sh`
- `data/sample_notes.jsonl`: sample notes

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## LLM Provider Configuration
### OpenAI
```env
LLM_PROVIDER=openai
LLM_API_KEY=<your_openai_key>
LLM_MODEL=gpt-4o-mini
```

### DeepSeek
```env
LLM_PROVIDER=deepseek
LLM_API_KEY=<your_deepseek_key>
LLM_MODEL=deepseek-chat
```

### Ollama
```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
# optional
# LLM_BASE_URL=http://localhost:11434/v1
```

### OpenAI-compatible endpoint
```env
LLM_PROVIDER=openai_compatible
LLM_API_KEY=<provider_key>
LLM_MODEL=<model_name>
LLM_BASE_URL=<https://your-endpoint/v1>
```

### Prompt version selection (optional)
```env
# If unset, each prompt uses its registry.yaml current_version.
INGESTION_PROMPT_VERSION=ingestion.extract.v7
ENVELOPE_REFINE_PROMPT_VERSION=envelope_refine.v1
CONTEXT_UPDATE_PROMPT_VERSION=context_update.v1
THINKING_PROMPT_VERSION=thinking.v1
```
Invalid prompt versions fail fast at runtime.

Thinking output controls:
```env
THINKING_OUTPUT_DIR=data/thinking_runs
THINKING_MAX_CARDS=200
THINKING_MAX_ENVELOPES=100
```

### Embedding configuration (optional)
```env
# Default is auto: use model-based embeddings when config is valid,
# otherwise fallback to lexical embeddings.
EMBEDDING_PROVIDER=auto
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=<optional, falls back to LLM_API_KEY>
EMBEDDING_BASE_URL=<optional, falls back to LLM_BASE_URL>
```

## Run
### Initialize DB
```bash
PYTHONPATH=src python scripts/init_db.py
```

### Ingest
```bash
PYTHONPATH=src python -m assistant.interfaces.cli.app ingest "Call Sarah about the Q3 budget next Monday"
```

### List cards / envelopes / context
```bash
PYTHONPATH=src python -m assistant.interfaces.cli.app cards-list
PYTHONPATH=src python -m assistant.interfaces.cli.app envelopes-list
PYTHONPATH=src python -m assistant.interfaces.cli.app context-show
PYTHONPATH=src python -m assistant.interfaces.cli.app context-show --derived
```

### Thinking cycle
```bash
PYTHONPATH=src python -m assistant.interfaces.cli.app thinking-run
PYTHONPATH=src python -m assistant.interfaces.cli.app thinking-artifacts-list --limit 20
PYTHONPATH=src python -m assistant.interfaces.cli.app thinking-show --file data/thinking_runs/<artifact>.json
```

### Interactive mode
```bash
PYTHONPATH=src python -m assistant.interfaces.cli.app interactive
```
Interactive commands:
- `ingest <note>`
- `cards [limit]`
- `envelopes`
- `envelope <id>`
- `context [--derived] [limit]`
- `thinking-run`
- `thinking-start [interval_seconds]`  # starts background scheduler
- `thinking-stop`                      # stops background scheduler
- `thinking-status`
- `artifacts [limit]`
- `show <artifact_path>`
- `exit`

Optional startup behavior:
```bash
PYTHONPATH=src python -m assistant.interfaces.cli.app interactive --thinking-trigger --thinking-interval-seconds 300
PYTHONPATH=src python -m assistant.interfaces.cli.app interactive --no-thinking-trigger
```

### Demo script
```bash
scripts/demo_ingest.sh
```

## Testing
```bash
PYTHONPATH=src pytest -q
```

## Prompt Snapshot Versioning
- Active runtime aliases: `ingestion.jinja`, `envelope_refine.jinja`, `context_update.jinja`, `thinking.jinja`
- Immutable snapshots: `<prompt_id>.vN.jinja`
- Shared registry metadata: `src/assistant/prompts/registry.yaml` (`prompts.<prompt_id>`)

Automated release command (recommended):
```bash
PYTHONPATH=src python scripts/release_prompt.py \
  --prompt-id ingestion \
  --changelog "Describe the prompt change"
```

Optional flags:
```bash
PYTHONPATH=src python scripts/release_prompt.py \
  --prompt-id context_update \
  --source-template context_update.jinja \
  --owner mle-team \
  --schema-version context_update.schema.v1 \
  --changelog "Describe the prompt change" \
  --dry-run
```

What the script updates:
1. Creates new immutable snapshot `<prompt_id>.v{N+1}.jinja`.
2. Updates `<prompt_id>.jinja` to match that snapshot exactly.
3. Updates `registry.yaml` for selected prompt_id (`current_version`, `current_template`, `versions[]`, `sha256`).

Runtime prompt selection:
1. Set per-agent prompt version env vars in `.env` to pin specific snapshots.
2. Leave them empty to use `registry.yaml` `prompts.<prompt_id>.current_version`.
3. Unknown or missing versions fail fast with a clear error.

## Persisted User Context
- Context is persisted in `user_context` (single snapshot row `id=1`).
- On each ingest, context is synchronously refreshed using:
  - recent/important evidence cards (10-12 total)
  - previous context snapshot for continuity
  - LLM structured update with strict schema
- If context LLM update fails, previous snapshot is kept (ingest continues).
