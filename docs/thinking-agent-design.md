# Thinking Agent Design (Scheduled)

## Goal
Run every hour to analyze cards, envelopes, and context signals and generate proactive suggestions.

## Input Data
- `cards`: status, due dates, assignee and envelope assignments
- `envelopes`: project/topic groupings
- derived context from card fields (assignees, keywords, recency)

## Output Data
- `thinking_runs`: execution/audit record for each schedule cycle
- `thinking_suggestions`: generated recommendations and conflict alerts

## Hourly Logic Flow
1. Start run: insert row in `thinking_runs` with `status=started`.
2. Collect active working set:
   - cards from recent window
   - envelopes with recent activity
   - top derived assignees/themes from cards
3. Apply suggestion rules:
   - Next Steps: envelope has pending items but no immediate next action
   - Recommendations: >=3 idea notes around same theme without focused envelope
   - Conflict Detection: same assignee with overlapping due windows
4. Deduplicate via `fingerprint` and skip already-open identical suggestions.
5. Persist suggestions and close run with summary.

## Operational Notes
- Designed for scheduler integration (cron or APScheduler).
- Suggestions are persistent and lifecycle-managed (`open`, `accepted`, `dismissed`, `expired`).
- Failure-safe by storing `failed` run status with error details in `summary_json`.
