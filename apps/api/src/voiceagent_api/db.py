from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from voiceagent_api.config import settings


class Base(DeclarativeBase):
    pass


def _create_engine():
    connect_args: dict[str, object] = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(settings.database_url, future=True, connect_args=connect_args)


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def create_database() -> None:
    Base.metadata.create_all(bind=engine)


def drop_database() -> None:
    Base.metadata.drop_all(bind=engine)


def ping_database() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
