"""Async SQLAlchemy database connection and session factory.
Supports both PostgreSQL (asyncpg) and SQLite (aiosqlite) backends.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    **({} if _is_sqlite else {
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    }),
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables if they do not already exist."""
    from app.models import database_models  # noqa: F401 — registers models with Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
