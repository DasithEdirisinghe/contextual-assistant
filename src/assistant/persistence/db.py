from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from assistant.config.settings import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    from assistant.persistence import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
