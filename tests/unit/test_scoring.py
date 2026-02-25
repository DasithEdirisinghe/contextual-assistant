from datetime import datetime

from assistant.config.settings import Settings
from assistant.db.models import EnvelopeORM
from assistant.services.scoring import EnvelopeScorer


def test_scorer_prefers_related_envelope() -> None:
    scorer = EnvelopeScorer(Settings())
    env1 = EnvelopeORM(id=1, name="Q3 Budget Project", summary="Finance planning", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    env2 = EnvelopeORM(id=2, name="Home Errands", summary="Personal tasks", created_at=datetime.utcnow(), updated_at=datetime.utcnow())

    result = scorer.choose_best(
        card_description="Call Sarah about quarterly budget",
        card_keywords=["budget", "q3", "sarah"],
        envelopes=[env1, env2],
    )
    assert result.envelope is not None
    assert result.envelope.name == "Q3 Budget Project"
