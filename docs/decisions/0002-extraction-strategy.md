# ADR 0002: Single Structured Extraction Call

## Decision
Use one schema-constrained extraction call for card type + entities + metadata.

## Context
Multiple LLM prompts increase cost, latency, and maintenance burden.

## Consequences
- Simpler orchestration and lower latency.
- Strong typed output contract with Pydantic/Instructor.
- Retry/fallback remains available for robustness.
