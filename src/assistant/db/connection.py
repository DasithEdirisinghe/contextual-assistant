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


def init_db() -> None:
    from assistant.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_cards_reasoning_steps_column()
