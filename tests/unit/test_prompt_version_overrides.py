import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from assistant.agents.thinking.agent import ThinkingAgent
from assistant.config.settings import Settings
from assistant.agents.context.updater import ContextUpdater
from assistant.agents.organization.refiner import EnvelopeRefiner
from assistant.db.base import Base


def test_envelope_refine_prompt_version_override_valid() -> None:
    settings = Settings(_env_file=None, ENVELOPE_REFINE_PROMPT_VERSION="envelope_refine.v2")
    svc = EnvelopeRefiner(settings)
    assert svc.prompt_version == "envelope_refine.v2"


def test_context_update_prompt_version_override_valid() -> None:
    settings = Settings(_env_file=None, CONTEXT_UPDATE_PROMPT_VERSION="context_update.v2")
    svc = ContextUpdater(settings)
    assert svc.prompt_version == "context_update.v2"


def test_context_update_prompt_version_override_invalid_fails_fast() -> None:
    settings = Settings(_env_file=None, CONTEXT_UPDATE_PROMPT_VERSION="context_update.v999")
    with pytest.raises(ValueError, match="Unknown prompt version"):
        ContextUpdater(settings)


def test_thinking_prompt_version_override_valid() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    settings = Settings(_env_file=None, THINKING_PROMPT_VERSION="thinking.v2")
    with Session() as session:
        agent = ThinkingAgent(session, settings)
    assert agent.prompt_version == "thinking.v2"
