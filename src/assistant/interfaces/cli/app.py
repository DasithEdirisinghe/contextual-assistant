import json
from typing import Optional

import typer

from assistant.config.logging import configure_logging
from assistant.config.settings import get_settings
from assistant.db.connection import SessionLocal, init_db
from assistant.db.models import CardORM, EnvelopeORM, EntityORM
from assistant.db.repo_context import ContextRepository
from assistant.db.repo_suggestions import SuggestionsRepository
from assistant.pipeline.orchestrator import AssistantOrchestrator

app = typer.Typer(help="Contextual Personal Assistant CLI")


@app.callback()
def main() -> None:
    configure_logging()
    init_db()


@app.command()
def ingest(note: str) -> None:
    """Ingest a raw note and generate structured card + envelope assignment."""
    settings = get_settings()
    with SessionLocal() as session:
        orchestrator = AssistantOrchestrator(session, settings)
        result = orchestrator.ingest_note(note)

    typer.echo("Card Created")
    typer.echo(json.dumps(result.model_dump(mode="json"), indent=2, default=str))


@app.command("cards-list")
def cards_list(limit: int = 20) -> None:
    with SessionLocal() as session:
        rows = session.query(CardORM).order_by(CardORM.created_at.desc()).limit(limit).all()
    for row in rows:
        typer.echo(
            f"[{row.id}] {row.card_type} | {row.description} | due={row.due_at} | envelope_id={row.envelope_id}"
        )


@app.command("envelopes-list")
def envelopes_list() -> None:
    with SessionLocal() as session:
        rows = session.query(EnvelopeORM).order_by(EnvelopeORM.updated_at.desc()).all()
    for row in rows:
        typer.echo(f"[{row.id}] {row.name} | {row.summary or '-'}")


@app.command("envelope-show")
def envelope_show(envelope_id: int) -> None:
    with SessionLocal() as session:
        envelope = session.query(EnvelopeORM).filter(EnvelopeORM.id == envelope_id).one_or_none()
        if envelope is None:
            typer.echo("Envelope not found")
            raise typer.Exit(code=1)
        typer.echo(f"Envelope [{envelope.id}] {envelope.name}")
        for card in envelope.cards:
            typer.echo(f"- card[{card.id}] {card.card_type}: {card.description}")


@app.command("context-show")
def context_show(limit: int = 10) -> None:
    with SessionLocal() as session:
        repo = ContextRepository(session)
        signals = repo.top_context_entities(limit=limit)
        ids = [s.entity_id for s in signals]
        entities = {e.id: e for e in session.query(EntityORM).filter(EntityORM.id.in_(ids)).all()} if ids else {}

    for signal in signals:
        entity = entities.get(signal.entity_id)
        if not entity:
            continue
        typer.echo(
            f"{entity.entity_type}:{entity.canonical_name} | strength={signal.strength:.2f} | mentions={signal.mention_count}"
        )


@app.command("thinking-sample")
def thinking_sample() -> None:
    """Show sample outputs from Thinking Agent examples."""
    sample = [
        {
            "type": "next_step",
            "message": "Q3 Budget envelope has pending tasks; start drafting finance summary.",
            "priority": "medium",
        },
        {
            "type": "conflict",
            "message": "Sarah has 2 tasks due on same date.",
            "priority": "high",
        },
    ]
    typer.echo(json.dumps(sample, indent=2))


@app.command("thinking-run")
def thinking_run() -> None:
    """Execute one full thinking cycle and persist suggestions."""
    settings = get_settings()
    with SessionLocal() as session:
        orchestrator = AssistantOrchestrator(session, settings)
        summary = orchestrator.run_thinking_cycle()
    typer.echo(json.dumps(summary.model_dump(), indent=2))


@app.command("thinking-list")
def thinking_list(status: Optional[str] = None, limit: int = 50) -> None:
    """List persisted thinking suggestions."""
    with SessionLocal() as session:
        repo = SuggestionsRepository(session)
        rows = repo.list_suggestions(status=status, limit=limit)

    for row in rows:
        typer.echo(
            f"[{row.id}] {row.suggestion_type} | priority={row.priority} | status={row.status} | {row.title}"
        )


if __name__ == "__main__":
    app()
