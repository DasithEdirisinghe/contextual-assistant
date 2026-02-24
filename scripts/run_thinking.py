from assistant.config.settings import get_settings
from assistant.db.connection import SessionLocal, init_db
from assistant.pipeline.orchestrator import AssistantOrchestrator


if __name__ == "__main__":
    init_db()
    settings = get_settings()
    with SessionLocal() as session:
        summary = AssistantOrchestrator(session, settings).run_thinking_cycle()
    print(summary.model_dump_json(indent=2))
