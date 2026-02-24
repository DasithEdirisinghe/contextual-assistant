from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from assistant.persistence.db import Base


class EnvelopeORM(Base):
    __tablename__ = "envelopes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    envelope_id: Mapped[int | None] = mapped_column(ForeignKey("envelopes.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    envelope: Mapped[EnvelopeORM | None] = relationship(back_populates="cards")
    entities: Mapped[list["CardEntityORM"]] = relationship(back_populates="card", cascade="all, delete-orphan")


class EntityORM(Base):
    __tablename__ = "entities"
    __table_args__ = (UniqueConstraint("entity_type", "canonical_name", name="uq_entity_type_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    card_links: Mapped[list["CardEntityORM"]] = relationship(back_populates="entity", cascade="all, delete-orphan")
    signal: Mapped["ContextSignalORM"] = relationship(back_populates="entity", uselist=False, cascade="all, delete-orphan")


class CardEntityORM(Base):
    __tablename__ = "card_entities"

    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(50), primary_key=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    card: Mapped[CardORM] = relationship(back_populates="entities")
    entity: Mapped[EntityORM] = relationship(back_populates="card_links")


class ContextSignalORM(Base):
    __tablename__ = "context_signals"

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), primary_key=True)
    strength: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    mention_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    entity: Mapped[EntityORM] = relationship(back_populates="signal")


class ThinkingRunORM(Base):
    __tablename__ = "thinking_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    window_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ThinkingSuggestionORM(Base):
    __tablename__ = "thinking_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("thinking_runs.id"), nullable=True)
    suggestion_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    related_refs_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


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
