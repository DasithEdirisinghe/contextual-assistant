from assistant.db.base import Base, SessionLocal, engine


def init_db() -> None:
    from assistant.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
