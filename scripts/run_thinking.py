from assistant.config.settings import get_settings
from assistant.agents.thinking.artifacts import write_run
from assistant.db.connection import SessionLocal, init_db
from assistant.pipeline.orchestrator import AssistantOrchestrator


if __name__ == "__main__":
    init_db()
    settings = get_settings()
    with SessionLocal() as session:
        output = AssistantOrchestrator(session, settings).run_thinking_cycle()
    path = write_run(output, settings.thinking_output_dir)
    print(f"artifact={path}")
    print(output.model_dump_json(indent=2))
