from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import HTTPBearer
import jwt
from jwt import PyJWKClient
from typing import Optional
from app.config import settings
from app.core.security import (
    create_access_token,
    TokenData,
)  # Your existing token creator
from fastapi import Request
from sqlalchemy import select
from app.models.db_models import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

security = HTTPBearer()
CLERK_JWKS_URL = settings.CLERK_JWKS_URL


async def get_user_by_clerk_id(clerk_id: str, db: AsyncSession = Depends(get_db)):
    """
    Find user by clerk_id (auth_id) and return the database user ID
    """
    try:
        # Find user in database where auth_id matches clerk_id
        result = await db.execute(select(User).where(User.auth_id == clerk_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return {
            "user_id": user.id,  # Return the database ID
            "clerk_id": clerk_id,  # For reference
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


async def permanently_delete_user(
    user_id: str, request: Request, db: AsyncSession
) -> dict:
    """
    Permanently deletes a user by ID (webhook-compatible).

    Args:
        user_id: ID of the user to delete
        request: The incoming request object
        db: Async database session

    Returns:
        dict: Webhook-compatible response message

    Raises:
        HTTPException: If user not found or deletion fails
    """
    try:
        # Check if user exists
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Permanent deletion within a transaction
        async with db.begin():
            await db.delete(user)
            # Explicit commit happens when transaction block exits successfully

        # Webhook response format
        return {"message": "User deleted successfully", "user_id": user_id}

    except HTTPException:
        # Re-raise known HTTP exceptions
        raise
    except Exception as e:
        # Handle any unexpected errors
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}",
        )
