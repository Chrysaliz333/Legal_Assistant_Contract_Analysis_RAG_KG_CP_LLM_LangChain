"""
Database connection management
Async PostgreSQL with SQLAlchemy 2.0
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
from config.settings import settings

# Create async engine
engine = create_async_engine(
    settings.get_database_url(),
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    echo=settings.DATABASE_ECHO,
    future=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for all models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes
    Provides database session with automatic cleanup
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialize database tables
    Only use in development - use Alembic migrations in production
    """
    from src.models import (
        User,
        Organization,
        NegotiationSession,
        DocumentVersion,
        Clause,
        Annotation,
        Policy,
        PlaybookRule,
        Finding,
        NeutralRationale,
        RationaleTransformation,
        SuggestedEdit,
        NegotiationLog,
        AuditLog,
        RejectedClause,
        Counterparty,
        CounterpartyProfile,
        Obligation,
        DriftAlert,
        ExceptionPattern,
    )

    async with engine.begin() as conn:
        # Drop all tables (DEVELOPMENT ONLY!)
        if settings.DEBUG:
            await conn.run_sync(Base.metadata.drop_all)

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    await engine.dispose()
