import json
from pathlib import Path
from typing import Optional

import typer
from sqlalchemy import create_engine, text

from assistant.config.logging import configure_logging
from assistant.config.settings import get_settings
from assistant.db.base import Base
from assistant.db.connection import SessionLocal, init_db
from assistant.db.models import CardORM, EnvelopeORM
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
            f"[{row.id}] {row.card_type} | {row.description} | due={row.due_at} | envelope_id={row.envelope_id} | keywords={','.join((row.keywords_json or [])[:5]) or '-'} | assignee={row.assignee_text}"
        )


@app.command("envelopes-list")
def envelopes_list() -> None:
    with SessionLocal() as session:
        rows = session.query(EnvelopeORM).order_by(EnvelopeORM.updated_at.desc()).all()
    for row in rows:
        typer.echo(
            f"[{row.id}] {row.name} | cards={row.card_count} | keywords={','.join((row.keywords_json or [])[:5]) or '-'} | {row.summary or '-'}"
        )


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
        rows = repo.top_context_entities(limit=limit)
    for row in rows:
        typer.echo(f"{row.label} | strength={row.strength:.2f} | mentions={row.mention_count}")


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


@app.command("db-reset")
def db_reset(
    database_url: Optional[str] = typer.Option(
        None,
        "--database-url",
        help="Target database URL. Defaults to DATABASE_URL from settings.",
    ),
    schema_mode: str = typer.Option(
        "orm",
        "--schema-mode",
        help="Schema bootstrap mode: 'orm' (SQLAlchemy metadata) or 'sql' (apply SQL script).",
    ),
    schema_file: Optional[Path] = typer.Option(
        None,
        "--schema-file",
        help="Path to SQL schema file when --schema-mode=sql.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Skip confirmation prompt.",
    ),
) -> None:
    """Drop and recreate tables in the target database."""
    settings = get_settings()
    target_url = database_url or settings.database_url

    if not yes:
        confirmed = typer.confirm(f"This will erase all data in: {target_url}. Continue?")
        if not confirmed:
            typer.echo("Cancelled.")
            raise typer.Exit(code=1)

    engine = create_engine(target_url, future=True)
    from assistant.db import models  # noqa: F401

    mode = schema_mode.strip().lower()
    if mode == "orm":
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        typer.echo(f"Database reset using ORM schema: {target_url}")
        return

    if mode == "sql":
        if schema_file is None:
            typer.echo("When --schema-mode=sql, --schema-file is required.")
            raise typer.Exit(code=2)
        if not schema_file.exists():
            typer.echo(f"Schema file not found: {schema_file}")
            raise typer.Exit(code=2)
        if not target_url.startswith("sqlite"):
            typer.echo("SQL schema mode currently supports only sqlite URLs.")
            raise typer.Exit(code=2)

        with engine.begin() as conn:
            table_names = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            ).scalars().all()
            for table_name in table_names:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))

        raw = engine.raw_connection()
        try:
            script = schema_file.read_text(encoding="utf-8")
            raw.executescript(script)
            raw.commit()
        finally:
            raw.close()
        typer.echo(f"Database reset using SQL schema file: {schema_file}")
        return

    typer.echo("Invalid --schema-mode. Use 'orm' or 'sql'.")
    raise typer.Exit(code=2)


if __name__ == "__main__":
    app()
