from datetime import datetime

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from assistant.agents.thinking.agent import ThinkingAgent
from assistant.agents.thinking.artifacts import list_artifacts, write_run
from assistant.config.settings import Settings
from assistant.db.base import Base
from assistant.db.models import CardORM, EnvelopeORM, UserContextORM


class _FakeStructuredInvoker:
    def invoke(self, _prompt: str):
        return {
            "suggestions": [
                {
                    "suggestion_type": "next_step",
                    "title": "Start Q3 Budget Draft",
                    "message": "Complete card #1 before other budget tasks.",
                    "priority": "high",
                    "score": 0.88,
                    "reasoning_steps": [
                        "Card #1 has near-term due date.",
                        "It is a prerequisite for related envelope tasks.",
                    ],
                    "evidence": {"card_ids": [1], "envelope_ids": [1], "context_keys": ["projects"]},
                }
            ]
        }


class _FakeLLM:
    def with_structured_output(self, _schema):
        return _FakeStructuredInvoker()


def test_thinking_cycle_generates_artifact_and_schema_without_db_persistence(monkeypatch, tmp_path) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    monkeypatch.setattr("assistant.agents.thinking.agent.build_chat_model", lambda _settings: _FakeLLM())
    settings = Settings(
        _env_file=None,
        THINKING_PROMPT_VERSION="thinking.v1",
        THINKING_OUTPUT_DIR=str(tmp_path),
    )

    with Session() as session:
        env = EnvelopeORM(name="Q3 Budget", summary="finance")
        session.add(env)
        session.flush()
        session.add(
            CardORM(
                raw_text="Prepare budget draft",
                card_type="task",
                description="Prepare budget draft",
                due_at=datetime(2026, 3, 1, 9, 0, 0),
                assignee_text="Sarah",
                keywords_json=["budget", "q3"],
                envelope_id=env.id,
            )
        )
        session.add(
            UserContextORM(
                id=1,
                context_json='{"projects":[{"name":"Q3 Budget","strength":0.9}]}',
                focus_summary="Q3 budget delivery",
                updated_at=datetime.utcnow(),
            )
        )
        session.commit()

        output = ThinkingAgent(session, settings).run_cycle()
        artifact = write_run(output, settings.thinking_output_dir)
        rows = list_artifacts(settings.thinking_output_dir, limit=10)

    assert artifact.exists()
    assert len(output.suggestions) == 1
    assert output.prompt_version == "thinking.v1"
    assert rows and rows[0].suggestions_count == 1

    # Ensure schema no longer includes obsolete thinking persistence tables.
    table_names = set(inspect(engine).get_table_names())
    assert "thinking_runs" not in table_names
    assert "thinking_suggestions" not in table_names
