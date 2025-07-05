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
from app.models.db_models import User, Notification, UserSettings, UserDevices
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
import logging
from sqlalchemy import select, delete


logger = logging.getLogger(__name__)

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
    Permanently deletes a user and all related data by ID (webhook-compatible).

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
        logger.info(f"Starting deletion process for user {user_id}")

        # Check if user exists
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"User {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        logger.info(f"Found user {user_id} ({user.email}). Preparing to delete...")

        # Permanent deletion within a transaction
        async with db.begin():
            try:
                # Delete dependent records first (order matters - child to parent)
                logger.debug(f"Deleting notifications for user {user_id}")
                await db.execute(
                    delete(Notification).where(Notification.user_id == user_id)
                )

                logger.debug(f"Deleting user devices for user {user_id}")
                await db.execute(
                    delete(UserDevices).where(UserDevices.user_id == user_id)
                )

                logger.debug(f"Deleting user settings for user {user_id}")
                await db.execute(
                    delete(UserSettings).where(UserSettings.owner_id == user_id)
                )

                # Add more dependent table deletions as needed
                # Example:
                # await db.execute(delete(UserProfile).where(UserProfile.user_id == user_id))

                logger.debug(f"Deleting main user record {user_id}")
                await db.delete(user)

                logger.info(f"Successfully deleted user {user_id} and all related data")

            except Exception as e:
                logger.error(f"Error during deletion of user {user_id}: {str(e)}")
                await db.rollback()
                raise

        # Webhook response format
        return {
            "message": "User and all related data deleted successfully",
            "user_id": user_id,
            "status": "success",
        }

    except HTTPException:
        logger.error(f"HTTPException occurred for user {user_id}", exc_info=True)
        raise
    except Exception as e:
        logger.critical(
            f"Unexpected error deleting user {user_id}: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}",
        )
