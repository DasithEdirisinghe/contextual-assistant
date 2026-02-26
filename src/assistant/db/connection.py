from sqlalchemy import inspect, text

from assistant.db.base import Base, SessionLocal, engine


def _ensure_cards_reasoning_steps_column() -> None:
    # Lightweight forward-only migration for local SQLite dev DBs.
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    if "cards" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("cards")}
    if "reasoning_steps_json" in columns:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE cards ADD COLUMN reasoning_steps_json JSON NOT NULL DEFAULT '[]'"))


def _ensure_envelopes_profile_columns() -> None:
    # Lightweight forward-only migration for local SQLite dev DBs.
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    if "envelopes" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("envelopes")}
    statements: list[str] = []
    if "keywords_json" not in columns:
        statements.append("ALTER TABLE envelopes ADD COLUMN keywords_json JSON NOT NULL DEFAULT '[]'")
    if "embedding_vector_json" not in columns:
        statements.append("ALTER TABLE envelopes ADD COLUMN embedding_vector_json JSON NOT NULL DEFAULT '[]'")
    if "card_count" not in columns:
        statements.append("ALTER TABLE envelopes ADD COLUMN card_count INTEGER NOT NULL DEFAULT 0")
    if "last_card_at" not in columns:
        statements.append("ALTER TABLE envelopes ADD COLUMN last_card_at DATETIME NULL")
    if statements:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))


def _ensure_user_context_table() -> None:
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    if "user_context" in inspector.get_table_names():
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE user_context (
                    id INTEGER PRIMARY KEY CHECK(id=1),
                    context_json TEXT NOT NULL,
                    focus_summary TEXT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )


def _drop_legacy_thinking_tables() -> None:
    # Thinking suggestions are now file artifacts; drop obsolete tables when present.
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS thinking_suggestions"))
        conn.execute(text("DROP TABLE IF EXISTS thinking_runs"))


def init_db() -> None:
    from assistant.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_cards_reasoning_steps_column()
    _ensure_envelopes_profile_columns()
    _ensure_user_context_table()
    _drop_legacy_thinking_tables()
