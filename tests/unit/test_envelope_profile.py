from datetime import datetime, timedelta

from assistant.config.settings import Settings
from assistant.db.models import CardORM
from assistant.services.envelope_profile import build_envelope_profile


def test_build_envelope_profile_derives_keywords_and_count() -> None:
    now = datetime.utcnow()
    cards = [
        CardORM(
            description="Call Sarah about Q3 budget",
            keywords_json=["q3", "budget", "call"],
            created_at=now,
        ),
        CardORM(
            description="Prepare Q3 budget slides",
            keywords_json=["q3", "budget", "slides"],
            created_at=now - timedelta(hours=1),
        ),
    ]
    profile = build_envelope_profile(cards, Settings(EMBEDDING_PROVIDER="lexical"))
    assert profile.card_count == 2
    assert "q3" in profile.keywords
    assert "budget" in profile.keywords
