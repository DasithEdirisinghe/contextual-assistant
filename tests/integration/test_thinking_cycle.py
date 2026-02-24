from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from assistant.agents.thinking_agent import ThinkingAgent
from assistant.config.settings import Settings
from assistant.db.base import Base
from assistant.db.models import CardORM, EnvelopeORM


def test_thinking_cycle_creates_suggestions_and_dedups() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    settings = Settings(database_url="sqlite+pysqlite:///:memory:")

    with Session() as session:
        env = EnvelopeORM(name="Q3 Budget", summary="finance")
        session.add(env)
        session.flush()

        session.add_all(
            [
                CardORM(
                    raw_text="Call Sarah about budget",
                    card_type="task",
                    description="Call Sarah about budget",
                    due_at=datetime(2026, 3, 1, 9, 0, 0),
                    assignee_text="Sarah",
                    keywords_json=["budget"],
                    envelope_id=env.id,
                ),
                CardORM(
                    raw_text="Send Sarah budget email",
                    card_type="task",
                    description="Send Sarah budget email",
                    due_at=datetime(2026, 3, 1, 13, 0, 0),
                    assignee_text="Sarah",
                    keywords_json=["budget"],
                    envelope_id=env.id,
                ),
                CardORM(
                    raw_text="Idea budget dashboard",
                    card_type="idea_note",
                    description="Budget dashboard",
                    due_at=None,
                    assignee_text=None,
                    keywords_json=["idea"],
                    envelope_id=env.id,
                ),
                CardORM(
                    raw_text="Idea budget workshop",
                    card_type="idea_note",
                    description="Budget workshop",
                    due_at=None,
                    assignee_text=None,
                    keywords_json=["idea"],
                    envelope_id=env.id,
                ),
                CardORM(
                    raw_text="Idea budget summary",
                    card_type="idea_note",
                    description="Budget summary",
                    due_at=None,
                    assignee_text=None,
                    keywords_json=["idea"],
                    envelope_id=env.id,
                ),
            ]
        )
        session.commit()

        service = ThinkingAgent(session, settings)
        first = service.run_cycle().model_dump()
        second = service.run_cycle().model_dump()

        assert first["created"] >= 2
        assert second["created"] == 0
        assert second["dedup_skipped"] >= first["created"]
