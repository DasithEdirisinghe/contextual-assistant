from sqlalchemy.orm import Session

from assistant.persistence.models import IngestionEventORM


class EventsRepository:
    def __init__(self, session: Session):
        self.session = session

    def log_ingestion(
        self,
        model_name: str,
        prompt_version: str,
        schema_version: str,
        success: bool,
        latency_ms: int,
        card_id: int | None = None,
        error_text: str | None = None,
    ) -> None:
        event = IngestionEventORM(
            card_id=card_id,
            model_name=model_name,
            prompt_version=prompt_version,
            schema_version=schema_version,
            success=success,
            latency_ms=latency_ms,
            error_text=error_text,
        )
        self.session.add(event)
