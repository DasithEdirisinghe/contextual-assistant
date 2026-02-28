from assistant.config.settings import get_settings
from assistant.db.connection import SessionLocal, init_db
from assistant.pipeline.orchestrator import AssistantOrchestrator

SAMPLE_NOTES = [
    "Call Sarah about the Q3 budget next Monday",
    "Idea: New logo should be blue and green",
    "Remember to pick up milk on the way home",
]


def main() -> None:
    init_db()
    settings = get_settings()
    with SessionLocal() as session:
        orchestrator = AssistantOrchestrator(session, settings)
        for note in SAMPLE_NOTES:
            result = orchestrator.ingest_note(note)
            print(f"Created card={result.card.id}, envelope={result.envelope_name}")


if __name__ == "__main__":
    main()
