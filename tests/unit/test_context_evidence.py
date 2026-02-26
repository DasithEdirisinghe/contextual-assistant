from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from assistant.agents.context.evidence import build_context_evidence
from assistant.db.base import Base
from assistant.db.models import CardORM, EnvelopeORM


def test_context_evidence_selector_returns_bounded_deduped_cards() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    with Session() as session:
        env = EnvelopeORM(name="Q3 Budget", summary="Finance")
        session.add(env)
        session.flush()
        now = datetime.utcnow()
        for idx in range(20):
            session.add(
                CardORM(
                    raw_text=f"note {idx}",
                    card_type="task" if idx % 2 == 0 else "idea_note",
                    description=f"description {idx}",
                    due_at=(now + timedelta(days=1)) if idx % 3 == 0 else None,
                    assignee_text="Sarah" if idx % 4 == 0 else None,
                    keywords_json=["budget", f"k{idx}"],
                    reasoning_steps_json=["step"],
                    envelope_id=env.id,
                    created_at=now - timedelta(minutes=idx),
                )
            )
        session.commit()

        evidence = build_context_evidence(session, max_cards=12)
        ids = [e.card_id for e in evidence]
        assert len(evidence) <= 12
        assert len(ids) == len(set(ids))
