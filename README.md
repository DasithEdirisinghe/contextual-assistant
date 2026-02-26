# Contextual Personal Assistant (Prototype)

A personal assistant that turns unstructured notes into structured cards, organizes them into envelopes, maintains user context, and generates proactive suggestions.

## Prerequisites
- Docker installed and running on host.
- Ollama installed on host.
- Python 3.11+ is only needed for non-Docker local runs.

## Step-by-Step Setup (Docker-First)

1. Clone and enter project root.
```bash
git clone https://github.com/DasithEdirisinghe/contextual-assistant.git
cd contextual-assistant
```

2. Build the Docker image.
```bash
docker build -t contextual-assistant:latest .
```

3. Pull required Ollama models on host.
```bash
ollama pull llama3.1:8b
ollama pull qwen3-embedding:0.6b
```

4. Start Ollama in a separate terminal.
```bash
ollama serve
```

## Configuration
Use `.env.docker` as default, or create `.env.docker.local` and pass it via `ENV_FILE`.

Required keys to verify:
```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
LLM_BASE_URL=http://host.docker.internal:11434/v1

EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=qwen3-embedding:0.6b
EMBEDDING_BASE_URL=http://host.docker.internal:11434/v1

DATABASE_URL=sqlite:///data/assistant-demo.db
```

Notes:
- If the DB file does not exist, SQLite creates it automatically.
- If it exists, the app reuses it.
- For normal usage, do not change these routing/scoring settings:
  - `ENVELOPE_ASSIGN_THRESHOLD`
  - `EMBEDDING_WEIGHT`
  - `KEYWORD_WEIGHT`
  - `ENTITY_WEIGHT`

## Run the App (Interactive)

Start the interactive assistant:
```bash
ENV_FILE=.env.docker.local ./scripts/docker_run.sh
```
(Or use `ENV_FILE=.env.docker` if you keep defaults there.)

What happens after launch:
- The container starts the interactive CLI prompt.
- You enter commands directly in that shell.

## First-Run Usage

Example commands inside interactive CLI:
- `ingest "Call Sarah about Q3 budget next Monday"`: Ingests a raw note and runs ingestion -> organization -> context update pipeline.
- `cards`: Lists recent cards with type, due date, envelope link, keywords, and assignee.
- `envelopes`: Lists envelopes with card count, top keywords, and summary.
- `context`: Shows the persisted user context snapshot (`user_context`).
- `thinking-start 3600`: Starts background thinking scheduler (every 3600 seconds).
- `thinking-status`: Shows whether thinking scheduler is running and current interval.
- `thinking-stop`: Stops background thinking scheduler.
- `artifacts`: Lists generated thinking suggestion artifact files.
- `show <artifact_path>`: Opens and prints one artifact JSON file.
- `exit`: Exits interactive CLI.

`exit` stops the CLI session and also stops the in-process thinking scheduler.




## Architecture & Design

### Why LangChain
- Runnable-based pipeline is used in this project:
  - Ingestion is implemented as composable LangChain runnable stages (prompt render -> model call -> parse/normalize), which keeps LLM behavior modular and testable.
- Schema-safe extraction contracts:
  - LangChain integrates cleanly with Pydantic structured outputs, so extracted fields map to strict card/context schemas instead of brittle text parsing.
- Future workflow scaling path:
  - If orchestration becomes more stateful/branching, this codebase can move naturally to LangGraph while keeping existing LangChain prompt/model/runnable components.

### Why SQLite + SQLAlchemy
- SQLite is chosen for assignment constraints and local-first execution:
  - zero external infrastructure,
  - file-based persistence,
  - simple Docker + local development workflow.
- SQLAlchemy is used for explicit schema modeling and repository boundaries:
  - clear table contracts,
  - controlled transactions in orchestrator flow,
  - easier migration of logic from Python loops into SQL queries where needed.

### Database Design
- `cards`:
  - Core normalized record for each ingested note.
  - Stores extracted operational fields used downstream (`card_type`, `description`, `due_at`, `assignee_text`, `keywords_json`, `envelope_id`, timestamps, reasoning).
- `envelopes`:
  - Represents higher-level grouping context.
  - Stores envelope profile fields (`name`, `summary`, `keywords_json`, `embedding_vector_json`, `card_count`, `last_card_at`) used for routing and refinement.
- `user_context`:
  - Single authoritative snapshot table (`id=1`) for current global user context and focus summary.
  - Snapshot model is intentional: retrieval is O(1) and no merge across historical rows is required at read time.
- `ingestion_events`:
  - Operational traceability for ingestion runs (prompt/model version observability and debugging).
- Thinking outputs:
  - Persisted as JSON artifacts in `data/thinking_runs` instead of DB tables to keep scheduled reasoning outputs append-only and easy to inspect/export.

### Database-Level Optimizations Implemented
- SQL-bounded reads at repository level:
  - `list_cards(limit=...)` and `list_envelopes(limit=...)` push limits to SQL instead of loading all rows and slicing in Python.
- SQL-first context evidence selection:
  - “Important card per envelope” selection is done with SQL window functions (`row_number() over (partition by envelope_id ...)`) instead of Python nested loops.
  - Final evidence card fetch is done in a consolidated query with required joins.
- Query-shape optimization over index tuning:
  - Current optimization strategy focuses on reducing scanned rows and moving ranking/filter logic into SQL.
  - Explicit ORM index declarations were intentionally not added in this phase (keeps schema simpler until profiling proves index need).

### Pipeline Explanation

Prompt-driven behavior:
- LLM-backed stages use versioned prompt templates from `src/assistant/prompts/`.
- Main prompt families:
  - `ingestion*.jinja` for ingestion extraction
  - `envelope_refine*.jinja` for envelope profile refinement
  - `context_update*.jinja` for context snapshot updates
  - `thinking*.jinja` for scheduled proactive reasoning
- Active prompt versions are resolved from config (`.env` / `.env.docker`) with registry validation.

### Ingestion Workflow

The ingestion workflow consists of three main agents working synchronously.

#### 1. Ingestion Agent
- **Input:** One raw user note (free text).
- **Processing:**
  - Uses the ingestion prompt template to extract:
    - `card_type`, `description`, `date_text`, `assignee`, `context_keywords`, `reasoning_steps`, `confidence`
  - Runs deterministic date resolution to convert `date_text` (for example, `next Monday`, `tonight`) into `due_at` when resolvable.
- **Output:** A validated card object ready for routing and persistence.
- **Stored in:** `cards` table (`description`, `card_type`, `due_at`, `assignee_text`, `keywords_json`, etc.).
- **Why it matters:** Converts ambiguous natural language into stable, machine-usable fields for downstream agents.

#### 2. Organization Agent
- **Input:** Newly extracted card + current envelope set.
- **Processing:**
  - Computes envelope match score using embedding similarity + keyword overlap.
  - Applies threshold-based decision:
    - assign to best existing envelope, or
    - create a new envelope when no strong match exists.
  - Uses envelope refine prompt template to update envelope profile (`name`, `summary`, `keywords`, embedding centroid) as cards accumulate.
- **Output:** Envelope assignment/creation decision and updated profile values.
- **Stored in:** `envelopes` table; card row is linked via `cards.envelope_id`.
- **Why it matters:** Keeps related notes grouped so retrieval and later reasoning operate on coherent context buckets.

#### 3. Context Agent
- **Input:** Latest persisted cards/envelopes + previous context snapshot.
- **Processing:**
  - Selects an evidence set (recent and important cards across active envelopes).
  - Uses context-update prompt template with previous snapshot + evidence cards.
  - Produces refreshed structured context buckets:
    - people, organizations, projects, themes, upcoming items, miscellaneous.
- **Output:** Updated context JSON and focus summary.
- **Stored in:** `user_context` table as a single authoritative row (`id=1`).
- **Why it matters:** Maintains evolving global user context that improves future organization and proactive suggestions.

### Thinking Agent Workflow (Scheduled)
- Input: current cards, envelopes, and persisted `user_context`.
- Processing:
  - Runs only when scheduler is enabled (`thinking-start`), at configured interval.
  - Uses thinking prompt template to generate proactive items in three classes:
    - `next_step`
    - `recommendation`
    - `conflict`
  - Attaches evidence references and reasoning steps for traceability.
- Output: structured suggestion bundle with run metadata.
- Stored in: JSON artifacts under `data/thinking_runs` (not persisted in DB suggestion tables).
- Why it matters: provides proactive assistant behavior beyond passive note storage.