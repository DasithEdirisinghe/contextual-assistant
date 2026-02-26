# Thinking Agent Design (Scheduled)

## Goal
Run every hour to analyze cards, envelopes, and persisted user context, then generate proactive suggestions.

## Input Data
- `cards`: type, description, due dates, assignee and envelope assignments
- `envelopes`: project/topic groupings
- `user_context`: latest structured snapshot (`context_json` + `focus_summary`)

## Output Data
- JSON artifact per run in `THINKING_OUTPUT_DIR` (default `data/thinking_runs`)
- Artifact includes:
  - run metadata (`run_id`, `generated_at`, `model_name`, `prompt_version`)
  - input stats (`cards_scanned`, `envelopes_scanned`)
  - structured suggestions with evidence and reasoning steps

## Hourly Logic Flow
1. Collect working set:
   - cards from recent window
   - envelopes with recent activity
   - latest persisted user context snapshot
2. Render versioned thinking prompt (`thinking.vN`) with few-shot guidance.
3. Invoke LLM with structured output schema:
   - `next_step`
   - `recommendation`
   - `conflict`
4. Validate schema output and write one artifact file atomically.

## Operational Notes
- Designed for scheduler integration (cron or APScheduler).
- Thinking DB tables are deprecated; suggestions are file artifacts only.
- Prompt version is configurable via `THINKING_PROMPT_VERSION` and resolved via prompt registry.
