from datetime import datetime

from assistant.config.settings import Settings
from assistant.domain.envelopes.matcher import EnvelopeMatcher
from assistant.persistence.models import EnvelopeORM


def test_envelope_match_prefers_related_name() -> None:
    settings = Settings()
    matcher = EnvelopeMatcher(settings)
    env1 = EnvelopeORM(id=1, name="Q3 Budget Project", summary="Finance planning", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    env2 = EnvelopeORM(id=2, name="Home Errands", summary="Personal tasks", created_at=datetime.utcnow(), updated_at=datetime.utcnow())

    result = matcher.choose_best(
        card_description="Call Sarah about quarterly budget",
        card_keywords=["budget", "q3", "sarah"],
        card_entities=["sarah"],
        envelopes=[env1, env2],
    )
    assert result.envelope is not None
    assert result.envelope.name == "Q3 Budget Project"
