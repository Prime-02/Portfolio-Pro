from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.config import settings
from typing import AsyncGenerator, Optional
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Database engine configuration with optimized settings for WebSockets
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,  # Reduce for Neon pooling
    max_overflow=20,  # Reduce overflow
    pool_pre_ping=True,  # Important for long-lived connections
    pool_recycle=3600,  # Recycle connections every hour
    pool_timeout=30,
    echo=settings.ENVIRONMENT == "development",
    future=True,
)

# Base session factory
BaseSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

Base = declarative_base()


# Regular HTTP request session (auto-closing)
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async generator for HTTP request database sessions (auto-closing)"""
    async with BaseSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


# WebSocket-specific session management
class WebSocketSessionManager:
    """Manages long-lived sessions for WebSocket connections"""

    @staticmethod
    @asynccontextmanager
    async def get_session() -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for WebSocket sessions that stays open until explicitly closed.
        Must be manually closed by the caller when the WebSocket disconnects.
        """
        session = BaseSessionLocal()
        try:
            yield session
        except Exception as e:
            logger.error(f"WebSocket session error: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def create_session() -> AsyncSession:
        """Create a new WebSocket session that must be manually closed"""
        return BaseSessionLocal()


# Schema verification (unchanged)
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


# For backward compatibility
get_websocket_db = WebSocketSessionManager.get_session
