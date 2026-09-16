from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


# ---------------------------------------------------------
# Async PostgreSQL engine
# ---------------------------------------------------------
#
# IMPORTANT FOR WINDOWS + CELERY + asyncpg:
# NullPool prevents SQLAlchemy from reusing an asyncpg connection
# created by an older asyncio event loop.
#
# This avoids:
#     RuntimeError: Event loop is closed
#
# which can happen when Celery tasks use asyncio.run(...).
# ---------------------------------------------------------

engine = create_async_engine(
    settings.DATABASE_URL,

    # SQL logs unnecessary during normal development.
    echo=False,

    # Do not keep/reuse pooled asyncpg connections across event loops.
    poolclass=NullPool,

    future=True,

    # Neon PostgreSQL requires SSL.
    connect_args={
        "ssl": "require",
    },
)


# ---------------------------------------------------------
# Async session factory
# ---------------------------------------------------------

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ---------------------------------------------------------
# SQLAlchemy Base
# ---------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------
# FastAPI database dependency
# ---------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()

        except Exception:
            await session.rollback()
            raise

        finally:
            await session.close()
