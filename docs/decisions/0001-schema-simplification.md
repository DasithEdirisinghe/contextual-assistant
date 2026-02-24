# ADR 0001: Simplified 8-Table Schema

## Decision
Use an 8-table SQLite schema to balance simplicity and future extensibility.

## Context
The assignment needs strong ingestion quality and maintainability over broad feature expansion.

## Consequences
- Faster implementation and testing.
- Lower join complexity.
- Preserves a migration path to more normalized/graph-heavy design if needed.
