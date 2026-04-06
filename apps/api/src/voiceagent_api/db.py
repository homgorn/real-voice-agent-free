from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from voiceagent_api.config import settings


class Base(DeclarativeBase):
    pass


def _to_async_url(url: str) -> str:
    if url.startswith("sqlite+pysqlite"):
        return url.replace("sqlite+pysqlite", "sqlite+aiosqlite")
    if url.startswith("postgresql+psycopg"):
        return url.replace("postgresql+psycopg", "postgresql+asyncpg")
    if url.startswith("postgresql+asyncpg") or url.startswith("sqlite+aiosqlite"):
        return url
    return url


def _to_sync_url(url: str) -> str:
    if url.startswith("sqlite+aiosqlite"):
        return url.replace("sqlite+aiosqlite", "sqlite+pysqlite")
    if url.startswith("postgresql+asyncpg"):
        return url.replace("postgresql+asyncpg", "postgresql+psycopg")
    return url


connect_args: dict[str, object] = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

is_sqlite = settings.database_url.startswith("sqlite") or settings.database_url.startswith("sqlite+aiosqlite")

if is_sqlite:
    sync_engine = create_engine(
        _to_sync_url(settings.database_url),
        future=True,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
    async_engine = create_async_engine(
        _to_async_url(settings.database_url),
        future=True,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
else:
    pool_size = getattr(settings, "db_pool_size", 5)
    max_overflow = getattr(settings, "db_max_overflow", 10)
    pool_recycle = getattr(settings, "db_pool_recycle", 3600)
    sync_engine = create_engine(
        _to_sync_url(settings.database_url),
        future=True,
        connect_args=connect_args,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=pool_recycle,
        pool_pre_ping=True,
    )
    async_engine = create_async_engine(
        _to_async_url(settings.database_url),
        future=True,
        connect_args=connect_args,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=pool_recycle,
        pool_pre_ping=True,
    )

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

SessionLocal = sessionmaker(
    bind=sync_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def _sync_create_database() -> None:
    Base.metadata.create_all(bind=sync_engine)


def _sync_drop_database() -> None:
    Base.metadata.drop_all(bind=sync_engine)


def _sync_ping_database() -> None:
    with sync_engine.connect() as connection:
        connection.execute(text("SELECT 1"))


async def create_database() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    await async_engine.dispose()


def drop_database() -> None:
    _sync_drop_database()


async def ping_database() -> None:
    async with async_engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


def get_sync_session():
    return SessionLocal()
