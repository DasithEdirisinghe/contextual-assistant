from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from assistant.db.base import Base
from assistant.db.models import CardORM, EnvelopeORM
from assistant.db.repo_cards import CardsRepository
from assistant.db.repo_envelopes import EnvelopesRepository


def test_cards_repo_list_cards_limit() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    with Session() as session:
        for i in range(8):
            session.add(
                CardORM(
                    raw_text=f"note {i}",
                    card_type="task",
                    description=f"desc {i}",
                    created_at=datetime.utcnow(),
                )
            )
        session.commit()
        repo = CardsRepository(session)
        rows = repo.list_cards(limit=5)
        assert len(rows) == 5


def test_envelopes_repo_list_envelopes_limit() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    with Session() as session:
        for i in range(8):
            session.add(EnvelopeORM(name=f"env-{i}", summary="x"))
        session.commit()
        repo = EnvelopesRepository(session)
        rows = repo.list_envelopes(limit=5)
        assert len(rows) == 5
