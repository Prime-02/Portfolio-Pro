from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.config import settings
from typing import AsyncGenerator
import logging
from fastapi import Request


logger = logging.getLogger(__name__)

# Database engine configuration
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=False,  # Disabled as we have proper connection handling
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_timeout=30,  # Wait 30 seconds for a connection
    echo=settings.ENVIRONMENT == "development",  # Only echo in development
    future=True,
)

# Session factory
SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async dependency that provides a database session"""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def verify_schema_exists():
    """Verify that the required schema exists without attempting to create it"""
    if "postgresql" in settings.DATABASE_URL:
        from sqlalchemy import text

        try:
            async with engine.begin() as conn:
                result = await conn.execute(
                    text(
                        "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'portfolio_pro_app'"
                    )
                )
                if not result.scalar():
                    logger.warning(
                        "Schema 'portfolio_pro_app' does not exist. Run migrations first."
                    )
        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            raise
