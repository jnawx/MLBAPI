from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

# ---------------------------------------------------------------------------
# Async engine & session (used by the FastAPI application)
# ---------------------------------------------------------------------------
async_engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=20,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Sync engine & session (used by ingestion / backfill scripts)
# ---------------------------------------------------------------------------
sync_engine = create_engine(
    settings.database_url_sync,
    echo=False,
    pool_size=10,
    max_overflow=5,
)

SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)
