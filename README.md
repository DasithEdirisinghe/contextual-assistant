# Contextual Personal Assistant

A personal assistant that turns unstructured notes into structured cards, organizes them into envelopes, maintains user context, and generates proactive suggestions.


## Prerequisites
- Docker installed and running on host.
- [Ollama](https://ollama.com/) installed on host.
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

Development note:
- `scripts/docker_run.sh` bind-mounts `src/` and `scripts/`, so code changes are available immediately after restarting the container.
- Rebuild image (`docker build ...`) only when dependencies or Dockerfile-level setup changes.

What happens after launch:
- The container starts the interactive CLI prompt.
- You enter commands directly in that shell.

Runtime disclaimer:
- This pipeline has been tested primarily with Ollama using `llama3.1:8b` as the LLM.
- If you switch to other LLMs/providers (including OpenAI), validate behavior separately.
- Current validation environment was macOS with 24 GB VRAM.
- It should work on other hosts, but for Ollama-based models use at least 16 GB VRAM for smoother execution.

## First-Run Usage

Example commands inside interactive CLI:
- `db-reset`: Clears and recreates the database schema (with confirmation prompt).
- `ingest "Call Sarah about Q3 budget next Monday"`: Ingests a raw note and runs ingestion -> organization -> context update pipeline.
- `cards`: Lists recent cards with type, due date, envelope link, keywords, and assignee.
- `envelopes [cards_per_envelope]`: Lists envelopes and previews recent cards in each envelope (default 5).
- `context`: Shows the persisted user context snapshot (`user_context`).
- `thinking-start 3600`: Starts background thinking scheduler (every 3600 seconds).
- `thinking-status`: Shows whether thinking scheduler is running and current interval.
- `thinking-stop`: Stops background thinking scheduler.
- `artifacts`: Lists generated thinking suggestion artifact files.
- `show <artifact_path>`: Opens and prints one artifact JSON file.
- `exit`: Exits interactive CLI.

`exit` stops the CLI session and also stops the in-process thinking scheduler.

### Interactive Demo Sequence
After the interactive shell starts, you can run this sequence directly:

```text
ingest "Book a hotel for next week trip with Gibson"
ingest "Do the Lit review of the TSRGS paper"
ingest "Buy a birthday present to mike"
ingest "Discuss the outcome of the TSRGS paper with Paul today"
ingest "Bring 1 litre of milk when way to home"
ingest "Ask Paul about his opinion on new research methodology of TSRGS paper"
ingest "Buy coffee and sugar for home"
cards
envelopes
```

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

<img src="assets/database_schema.png" alt="Database Schema" height="400"/>

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

### High Level Flow Diagram

<img src="assets/high_level_diagram.png" alt="High Level Diagram" width="800" />

### Ingestion Workflow

#### 1) Ingestion Agent
- The ingestion stage converts free-text notes into strict structured output:
  - `card_type`, `description`, `date_text`, `assignee`, `context_keywords`, `reasoning_steps`, `confidence`.
- Strict schema validation is used because every downstream stage depends on these fields.
- `date_text` is resolved deterministically into `due_at` so temporal interpretation is stable across runs and not dependent on LLM variance.
- This contract-first design reduces ambiguity propagation and makes organization/context/thinking behavior more reliable.

#### 2) Organization Agent
- Envelope assignment uses a hybrid scoring function:
  - `final_score = EMBEDDING_WEIGHT * semantic_similarity + KEYWORD_WEIGHT * keyword_overlap + ENTITY_WEIGHT * assignee_bonus`
- Decision policy:
  - if best score >= `ENVELOPE_ASSIGN_THRESHOLD` -> assign to existing envelope,
  - else create a new envelope.
- Why this hybrid approach:
  - embeddings capture semantic similarity,
  - keyword overlap keeps lexical precision,
  - assignee bonus helps person-centric clustering.
- After assignment, envelope profile is refreshed:
  - deterministic profile updates (keywords, embedding centroid, counters),
  - LLM-based refinement for envelope name/summary text quality.
- Design tradeoff:
  - routing decision is deterministic and explainable,
  - LLM is used where language quality matters most (profile text refinement).

#### 3) Storage progression rationale
- Card is persisted with envelope linkage.
- Envelope state is updated so future matching quality improves with accumulated data.
- This creates a progressively better organization loop with each ingested note.

### Context Agent Logic

#### 1) Evidence selection strategy
- Context updates are not based on full history every time.
- Evidence set is built from:
  - latest global cards,
  - top “important” cards from active envelopes.
- This keeps prompts focused, reduces noise, and scales better than sending all cards.

#### 2) Prompting strategy for context refinement
- Context update prompt receives:
  - previous snapshot,
  - current evidence cards.
- Why:
  - previous snapshot provides continuity,
  - evidence cards provide recency grounding.
- This supports stable evolution of context instead of abrupt context drift.

#### 3) Structured context output
- Output buckets are explicit:
  - people, organizations, projects, themes, important_upcoming, miscellaneous.
- Focus summary is generated as a concise human-readable view of current priorities.
- Structured output is used to keep downstream consumption deterministic.

#### 4) Persistence model
- Context is stored as one authoritative snapshot row (`user_context.id=1`).
- This gives simple O(1) read access for routing/thinking and avoids expensive merge logic at read time.

### Reasoning-Centric Thinking Agent

#### 1) Why scheduled/triggered
- Thinking runs are decoupled from synchronous ingestion.
- This keeps note ingestion responsive while still enabling proactive assistant behavior.

#### 2) What data it analyzes
- Thinking consumes:
  - cards (task/reminder/idea-level details),
  - envelopes (group-level context),
  - persisted user context (global priorities).
- Combining local + grouped + global signals improves suggestion relevance.

#### 3) Why reasoning-based prompting
- Thinking is a cross-entity reasoning problem, not simple extraction.
- Prompting is designed to produce:
  - `next_step`,
  - `recommendation`,
  - `conflict`.
- `reasoning_steps` and evidence IDs are included for transparency and inspectability.

#### 4) Why JSON structured output and artifacts
- JSON schema ensures deterministic parsing and safe downstream automation.
- Thinking results are written to artifact files (`data/thinking_runs`) for auditable, reproducible outputs without coupling to additional DB tables.


--------------------------



### Use of AI Tools

AI tools were used as engineering accelerators during this project.

- Tools used:
  - Cursor + Codex was used for design iteration, refactoring guidance, and documentation improvements.
- Role of AI assistance:
  - architecture alternative brainstorming,
  - code scaffolding/refactoring support,
  - prompt drafting and refinement,
  - test-case idea generation,
  - README wording and structure improvements.
- Human validation:
  - final implementation decisions, code review, and behavior checks were manually validated.
  - test suites and manual CLI checks were used to verify system behavior.


## Potential Next-Step Improvements

1. Decouple synchronous ingest path from heavy post-processing  
Move envelope refinement and context refresh to async workers so note ingestion stays fast under load.

2. Incremental envelope profile updates  
Replace full envelope recomputation on each ingest with incremental updates (embedding centroid, keyword profile, counters), and run periodic full rebuilds only as maintenance.

3. Multi-user data model  
Add `user_id` scoping to cards, envelopes, events, and context snapshot for tenant isolation and true product-scale behavior.

4. Production database + migrations  
Move from SQLite to PostgreSQL for higher concurrency and introduce migration tooling (e.g., Alembic) for controlled schema evolution.

5. LLM reliability and cost controls  
Standardize timeout/retry policies, add extraction validation gates, and log per-agent latency/token usage/cost telemetry.

6. Thinking pipeline efficiency  
Add deterministic candidate pre-filtering before LLM reasoning so thinking runs stay bounded as dataset size grows.

7. Operational observability  
Introduce request tracing and agent-level metrics (latency, failure rate, confidence distribution) with clear SLO/alert thresholds.


-------------------------------


#### Optional: Prompt Versioning (Per Agent)

Use this only if you want to create and test new prompt versions.

Versioned prompts live in `src/assistant/prompts/` and are tracked in `registry.yaml`.

##### 0. Update the active prompt template first
Before releasing a new version, edit the active alias file for that agent:
- `src/assistant/prompts/ingestion.jinja`
- `src/assistant/prompts/envelope_refine.jinja`
- `src/assistant/prompts/context_update.jinja`
- `src/assistant/prompts/thinking.jinja`

##### 1. Create a new prompt version
Use the generic release script:

```bash
python scripts/release_prompt.py \
  --prompt-id <ingestion|envelope_refine|context_update|thinking> \
  --changelog "short change summary" \
  --owner "<your_name_or_team>"
```

Examples:

```bash
python scripts/release_prompt.py --prompt-id ingestion --changelog "Improve assignee extraction examples" --owner "mle-team"
python scripts/release_prompt.py --prompt-id envelope_refine --changelog "Refine envelope title constraints" --owner "mle-team"
python scripts/release_prompt.py --prompt-id context_update --changelog "Improve evidence weighting rules" --owner "mle-team"
python scripts/release_prompt.py --prompt-id thinking --changelog "Add conflict-detection few-shot" --owner "mle-team"
```

What this does:
- creates immutable snapshot `<prompt_id>.vN.jinja`
- updates active alias `<prompt_id>.jinja`
- updates `registry.yaml` (`current_version`, `current_template`, changelog, sha256)

##### 2. Activate a prompt version via env
Set the corresponding env key in `.env`, `.env.docker`, or `.env.docker.local`:

```env
INGESTION_PROMPT_VERSION=ingestion.extract.v11
ENVELOPE_REFINE_PROMPT_VERSION=envelope_refine.v2
CONTEXT_UPDATE_PROMPT_VERSION=context_update.v2
THINKING_PROMPT_VERSION=thinking.v2
```