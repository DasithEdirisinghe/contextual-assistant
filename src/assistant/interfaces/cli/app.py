import json
import shlex
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from sqlalchemy import MetaData, create_engine, text

from assistant.agents.thinking.artifacts import list_artifacts, write_run
from assistant.config.logging import configure_logging
from assistant.config.settings import Settings, get_settings
from assistant.db.base import Base
from assistant.db.connection import SessionLocal, init_db
from assistant.db.models import CardORM, EnvelopeORM
from assistant.db.repo_context import ContextRepository
from assistant.pipeline.orchestrator import AssistantOrchestrator

app = typer.Typer(help="Contextual Personal Assistant CLI")


@app.callback()
def main() -> None:
    configure_logging()
    init_db()


def _ok(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.GREEN, bold=True)


def _info(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.CYAN)


def _warn(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.YELLOW, bold=True)


def _err(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, bold=True)


def _run_ingest(settings: Settings, note: str) -> dict:
    with SessionLocal() as session:
        orchestrator = AssistantOrchestrator(session, settings)
        result = orchestrator.ingest_note(note)
    payload = result.model_dump(mode="json")
    _ok("Card Created")
    typer.echo(json.dumps(payload, indent=2, default=str))
    return payload


def _run_cards_list(limit: int) -> None:
    with SessionLocal() as session:
        rows = session.query(CardORM).order_by(CardORM.created_at.desc()).limit(limit).all()
    for row in rows:
        typer.echo(
            f"[{row.id}] {row.card_type} | {row.description} | due={row.due_at} | envelope_id={row.envelope_id} | "
            f"keywords={','.join((row.keywords_json or [])[:5]) or '-'} | assignee={row.assignee_text}"
        )


def _run_envelopes_list() -> None:
    with SessionLocal() as session:
        rows = session.query(EnvelopeORM).order_by(EnvelopeORM.updated_at.desc()).all()
    for row in rows:
        typer.echo(
            f"[{row.id}] {row.name} | cards={row.card_count} | "
            f"keywords={','.join((row.keywords_json or [])[:5]) or '-'} | {row.summary or '-'}"
        )


def _run_envelope_show(envelope_id: int) -> None:
    with SessionLocal() as session:
        envelope = session.query(EnvelopeORM).filter(EnvelopeORM.id == envelope_id).one_or_none()
        if envelope is None:
            typer.echo("Envelope not found")
            raise typer.Exit(code=1)
        typer.echo(f"Envelope [{envelope.id}] {envelope.name}")
        for card in envelope.cards:
            typer.echo(f"- card[{card.id}] {card.card_type}: {card.description}")


def _run_context_show(limit: int, derived: bool) -> None:
    with SessionLocal() as session:
        repo = ContextRepository(session)
        persisted = None if derived else repo.get_persisted_context()
        if persisted is not None:
            typer.echo(json.dumps(persisted, indent=2, default=str))
            return
        rows = repo.top_context_entities(limit=limit)
    for row in rows:
        typer.echo(f"{row.label} | strength={row.strength:.2f} | mentions={row.mention_count}")


def _run_thinking_cycle(settings: Settings, *, emit_header: bool = True) -> dict:
    with SessionLocal() as session:
        orchestrator = AssistantOrchestrator(session, settings)
        output = orchestrator.run_thinking_cycle()
    artifact_path = write_run(output, settings.thinking_output_dir)
    payload = output.model_dump(mode="json")
    payload["artifact_path"] = str(artifact_path)
    if emit_header:
        _info(f"artifact={artifact_path}")
        typer.echo(json.dumps(payload, indent=2, default=str))
    return payload


def _run_thinking_artifacts_list(settings: Settings, limit: int = 20) -> None:
    rows = list_artifacts(settings.thinking_output_dir, limit=limit)
    for row in rows:
        typer.echo(
            f"{row.generated_at} | suggestions={row.suggestions_count} | types={row.by_type} | {row.artifact_path}"
        )


def _run_thinking_show(file: Path) -> None:
    if not file.exists():
        _err(f"artifact not found: {file}")
        raise typer.Exit(code=1)
    payload = json.loads(file.read_text(encoding="utf-8"))
    typer.echo(json.dumps(payload, indent=2, default=str))


@app.command()
def ingest(note: str) -> None:
    """Ingest a raw note and generate structured card + envelope assignment."""
    _run_ingest(get_settings(), note)


@app.command("cards-list")
def cards_list(limit: int = 20) -> None:
    _run_cards_list(limit)


@app.command("envelopes-list")
def envelopes_list() -> None:
    _run_envelopes_list()


@app.command("envelope-show")
def envelope_show(envelope_id: int) -> None:
    _run_envelope_show(envelope_id)


@app.command("context-show")
def context_show(limit: int = 10, derived: bool = False) -> None:
    _run_context_show(limit=limit, derived=derived)


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
    """Execute one thinking cycle and persist the output as a JSON artifact."""
    _run_thinking_cycle(get_settings())


@app.command("thinking-artifacts-list")
def thinking_artifacts_list(limit: int = 20) -> None:
    """List thinking artifact files from local output directory."""
    _run_thinking_artifacts_list(get_settings(), limit=limit)


@app.command("thinking-show")
def thinking_show(file: Path) -> None:
    """Show one thinking artifact JSON file."""
    _run_thinking_show(file)


def _interactive_help() -> None:
    _info(
        "\n".join(
            [
                "Interactive commands:",
                "  help",
                "  ingest <note>",
                "  cards [limit]",
                "  envelopes",
                "  envelope <id>",
                "  context [--derived] [limit]",
                "  thinking-run",
                "  thinking-start [interval_seconds]",
                "  thinking-stop",
                "  thinking-status",
                "  artifacts [limit]",
                "  show <artifact_path>",
                "  clear",
                "  quit | exit",
            ]
        )
    )


def _start_thinking_trigger(
    settings: Settings,
    *,
    interval_seconds: int,
    stop_event: threading.Event,
) -> threading.Thread:
    def _worker() -> None:
        while not stop_event.wait(interval_seconds):
            try:
                payload = _run_thinking_cycle(settings, emit_header=False)
                suggestions = payload.get("suggestions", [])
                artifact_path = payload.get("artifact_path")
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                _ok(
                    f"\n[thinking-trigger] Thinking Agent triggered at {now}. "
                    f"suggestions={len(suggestions)}"
                )
                _info(f"[thinking-trigger] latest suggestions file: {artifact_path}")
                _info(f"[thinking-trigger] run: show {artifact_path}")
                if suggestions:
                    top = suggestions[0]
                    _warn(
                        f"[thinking-trigger] top={top.get('suggestion_type')} | {top.get('title')}"
                    )
            except Exception as exc:  # noqa: BLE001
                _err(f"\n[thinking-trigger] failed: {exc}")

    thread = threading.Thread(target=_worker, daemon=True, name="thinking-trigger")
    thread.start()
    return thread


@app.command("interactive")
def interactive(
    thinking_trigger: bool = typer.Option(
        False,
        "--thinking-trigger/--no-thinking-trigger",
        help="Start periodic thinking cycles immediately on interactive shell startup.",
    ),
    thinking_interval_seconds: int = typer.Option(
        3600,
        "--thinking-interval-seconds",
        min=30,
        help="Thinking trigger interval in seconds.",
    ),
) -> None:
    """Start interactive CLI session for note ingestion and live assistant operations."""
    settings = get_settings()
    trigger_state: dict[str, object] = {
        "stop_event": None,
        "thread": None,
        "interval_seconds": thinking_interval_seconds,
    }

    def _trigger_enabled() -> bool:
        thread = trigger_state.get("thread")
        return isinstance(thread, threading.Thread) and thread.is_alive()

    def _trigger_start(interval_seconds: int) -> None:
        if _trigger_enabled():
            _warn("thinking trigger already running")
            return
        stop_event = threading.Event()
        thread = _start_thinking_trigger(
            settings,
            interval_seconds=interval_seconds,
            stop_event=stop_event,
        )
        trigger_state["stop_event"] = stop_event
        trigger_state["thread"] = thread
        trigger_state["interval_seconds"] = interval_seconds
        _ok(f"thinking trigger started (interval={interval_seconds}s)")

    def _trigger_stop(*, quiet: bool = False) -> None:
        if not _trigger_enabled():
            if not quiet:
                _warn("thinking trigger is not running")
            return
        stop_event = trigger_state.get("stop_event")
        thread = trigger_state.get("thread")
        if isinstance(stop_event, threading.Event):
            stop_event.set()
        if isinstance(thread, threading.Thread):
            thread.join(timeout=1.0)
        trigger_state["stop_event"] = None
        trigger_state["thread"] = None
        if not quiet:
            _ok("thinking trigger stopped")

    if thinking_trigger:
        _trigger_start(thinking_interval_seconds)

    typer.clear()
    _ok("Interactive mode started.")
    _info("Welcome to Contextual Assistant interactive shell.")
    _info("Helper commands are available below:")
    _interactive_help()
    while True:
        try:
            line = input(typer.style("assistant> ", fg=typer.colors.BRIGHT_CYAN, bold=True)).strip()
        except (EOFError, KeyboardInterrupt):
            typer.echo("")
            break
        if not line:
            continue

        try:
            parts = shlex.split(line)
        except ValueError as exc:
            _err(f"parse error: {exc}")
            continue
        cmd = parts[0].lower()
        args = parts[1:]

        try:
            if cmd in {"quit", "exit"}:
                break
            if cmd == "help":
                _interactive_help()
            elif cmd == "ingest":
                if not args:
                    _warn("usage: ingest <note>")
                    continue
                _run_ingest(settings, " ".join(args))
            elif cmd == "cards":
                limit = int(args[0]) if args else 20
                _run_cards_list(limit)
            elif cmd == "envelopes":
                _run_envelopes_list()
            elif cmd == "envelope":
                if not args:
                    _warn("usage: envelope <id>")
                    continue
                _run_envelope_show(int(args[0]))
            elif cmd == "context":
                derived = "--derived" in args
                clean_args = [a for a in args if a != "--derived"]
                limit = int(clean_args[0]) if clean_args else 10
                _run_context_show(limit=limit, derived=derived)
            elif cmd == "thinking-run":
                _run_thinking_cycle(settings)
            elif cmd == "thinking-start":
                interval = int(args[0]) if args else int(trigger_state["interval_seconds"])
                if interval < 30:
                    _warn("minimum interval is 30 seconds")
                    continue
                _trigger_start(interval)
            elif cmd == "thinking-stop":
                _trigger_stop()
            elif cmd == "thinking-status":
                status = "running" if _trigger_enabled() else "stopped"
                color_msg = f"thinking trigger: {status} (interval={trigger_state['interval_seconds']}s)"
                if status == "running":
                    _ok(color_msg)
                else:
                    _warn(color_msg)
            elif cmd == "artifacts":
                limit = int(args[0]) if args else 20
                _run_thinking_artifacts_list(settings, limit=limit)
            elif cmd == "show":
                if not args:
                    _warn("usage: show <artifact_path>")
                    continue
                _run_thinking_show(Path(args[0]))
            elif cmd == "clear":
                typer.clear()
                _ok("Screen cleared. Type `help` for commands.")
            else:
                _warn(f"unknown command: {cmd}")
        except Exception as exc:  # noqa: BLE001
            _err(f"command failed: {exc}")

    _trigger_stop(quiet=True)
    _ok("Interactive mode exited.")


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
        reflected = MetaData()
        reflected.reflect(bind=engine)
        reflected.drop_all(bind=engine)
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
