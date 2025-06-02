from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session  # Your session factory

async def get_db() -> AsyncSession:  # Return type hint
    async with async_session() as session:
        yield session