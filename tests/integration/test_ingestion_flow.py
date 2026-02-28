import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from assistant.config.settings import Settings
from assistant.pipeline.orchestrator import AssistantOrchestrator
from assistant.db.base import Base
from assistant.db.models import CardORM, EnvelopeORM, IngestionEventORM, UserContextORM


def test_ingestion_creates_card_and_envelope() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    settings = Settings(
        llm_provider="openai",
        llm_api_key=None,
        database_url="sqlite+pysqlite:///:memory:",
        INGESTION_PROMPT_VERSION="ingestion.extract.v11",
    )

    with Session() as session:
        orchestrator = AssistantOrchestrator(session, settings)
        result = orchestrator.ingest_note("Call Sarah about the Q3 budget next Monday")

        cards = session.query(CardORM).all()
        envelopes = session.query(EnvelopeORM).all()
        events = session.query(IngestionEventORM).all()
        context_rows = session.query(UserContextORM).all()

    assert result.card.id > 0
    assert len(cards) == 1
    assert len(envelopes) == 1
    assert envelopes[0].id == cards[0].envelope_id
    assert envelopes[0].card_count == 1
    assert isinstance(envelopes[0].keywords_json, list)
    assert len(envelopes[0].keywords_json) >= 1
    assert cards[0].due_at is not None
    assert isinstance(cards[0].reasoning_steps_json, list)
    assert len(cards[0].reasoning_steps_json) >= 1
    assert len(events) == 1
    assert events[0].prompt_version == "ingestion.extract.v11"
    assert len(context_rows) <= 1


def test_ingestion_invalid_prompt_version_fails_fast() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    settings = Settings(
        llm_provider="openai",
        llm_api_key=None,
        database_url="sqlite+pysqlite:///:memory:",
        INGESTION_PROMPT_VERSION="ingestion.extract.v999",
    )

    with Session() as session:
        with pytest.raises(ValueError, match="Unknown prompt version"):
            AssistantOrchestrator(session, settings)
