from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from assistant.db.base import Base
from assistant.db.repo_context_snapshot import ContextSnapshotRepository


def test_context_snapshot_upsert_singleton_row() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    with Session() as session:
        repo = ContextSnapshotRepository(session)
        first = repo.upsert_snapshot(context_json='{"themes":[]}', focus_summary="initial", updated_at=datetime.utcnow())
        second = repo.upsert_snapshot(context_json='{"themes":["budget"]}', focus_summary="updated", updated_at=datetime.utcnow())
        session.commit()
        assert first.id == 1
        assert second.id == 1
        fetched = repo.get_snapshot()
        assert fetched is not None
        assert fetched.id == 1
        assert "budget" in fetched.context_json
