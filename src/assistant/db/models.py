from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from assistant.db.base import Base


class EnvelopeORM(Base):
    __tablename__ = "envelopes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    embedding_vector_json: Mapped[list[float]] = mapped_column(JSON, default=list, nullable=False)
    card_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_card_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    cards: Mapped[list["CardORM"]] = relationship(back_populates="envelope")


class CardORM(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    card_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assignee_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    keywords_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    reasoning_steps_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    envelope_id: Mapped[int | None] = mapped_column(ForeignKey("envelopes.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    envelope: Mapped[EnvelopeORM | None] = relationship(back_populates="cards")


class IngestionEventORM(Base):
    __tablename__ = "ingestion_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int | None] = mapped_column(ForeignKey("cards.id"), nullable=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    success: Mapped[bool] = mapped_column(default=True, nullable=False)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class UserContextORM(Base):
    __tablename__ = "user_context"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    context_json: Mapped[str] = mapped_column(Text, nullable=False)
    focus_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


__all__ = [
    "EnvelopeORM",
    "CardORM",
    "IngestionEventORM",
    "UserContextORM",
]
