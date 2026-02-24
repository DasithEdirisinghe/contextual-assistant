from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from assistant.config.settings import Settings
from assistant.orchestration.ingestion_agent import IngestionAgent
from assistant.persistence.db import Base
from assistant.persistence.models import CardORM, EnvelopeORM


def test_ingestion_creates_card_and_envelope() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    settings = Settings(openai_api_key=None, database_url="sqlite+pysqlite:///:memory:")

    with Session() as session:
        agent = IngestionAgent(session, settings)
        result = agent.ingest("Call Sarah about the Q3 budget next Monday")

        cards = session.query(CardORM).all()
        envelopes = session.query(EnvelopeORM).all()

    assert result.card.id > 0
    assert len(cards) == 1
    assert len(envelopes) == 1
    assert envelopes[0].id == cards[0].envelope_id
