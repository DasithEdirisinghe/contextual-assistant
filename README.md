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
- `src/assistant/agents/*_agent.py`: ingestion/organization/context/thinking agents
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
# If unset, ingestion uses registry.yaml current_version.
INGESTION_PROMPT_VERSION=ingestion.extract.v7
```
Invalid prompt versions fail fast at runtime.

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
```

### Thinking cycle
```bash
PYTHONPATH=src python -m assistant.interfaces.cli.app thinking-run
PYTHONPATH=src python -m assistant.interfaces.cli.app thinking-list --status open --limit 20
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
- Active runtime alias: `src/assistant/prompts/ingestion.jinja`
- Immutable snapshots: `ingestion.v1.jinja` ... latest `ingestion.vN.jinja`
- Registry metadata: `src/assistant/prompts/registry.yaml`

Automated release command (recommended):
```bash
PYTHONPATH=src python scripts/release_ingestion_prompt.py \
  --changelog "Describe the prompt change"
```

Optional flags:
```bash
PYTHONPATH=src python scripts/release_ingestion_prompt.py \
  --source-template ingestion.jinja \
  --owner mle-team \
  --schema-version ingestion.schema.v4 \
  --changelog "Describe the prompt change" \
  --dry-run
```

What the script updates:
1. Creates new immutable snapshot `ingestion.v{N+1}.jinja`.
2. Updates `ingestion.jinja` to match that snapshot exactly.
3. Updates `registry.yaml` (`current_version`, `current_template`, `versions[]`, `sha256`).

Runtime prompt selection:
1. Set `INGESTION_PROMPT_VERSION` in `.env` to pin a specific snapshot.
2. Leave it empty to use `registry.yaml` `current_version`.
3. Unknown or missing versions fail fast with a clear error.
