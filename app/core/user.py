from typing import Dict, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, insert
from app.models.db_models import User, UserProfile, UserSettings
from app.models.schemas import (
    UserSettingsBase,
    UserProfileRequest,
    UserUpdateRequest,
    UserUpdateRequest,
    UserProjectAssociation,
)
from app.core.security import get_current_user
from fastapi import HTTPException, status, Depends
from sqlalchemy import Boolean, cast
from app.database import get_db
from app.core.security import validate_username
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
import uuid
import re
import unicodedata


async def get_common_params(
    data: Dict[str, Union[str, bool]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": data, "user": user, "db": db}


unathorized = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,  # More appropriate status code
    detail="Authentication required",
)


async def update_user_info(
    commons: dict = Depends(get_common_params),
) -> UserUpdateRequest:
    update_data = commons["data"]
    user = commons["user"]
    db = commons["db"]
    """Update user information in the database."""
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided"
        )

    # Filter out None values and create update dictionary
    valid_updates = {k: v for k, v in update_data.items() if v != ""}
    if "username" in valid_updates:
        if not validate_username(str(valid_updates["username"])):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid username format",
            )

        # Validate username format
    if not valid_updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update"
        )

    try:
        # Build the update statement
        stmt = (
            update(User)
            .where(cast(User.id == user.id, Boolean))
            .values(**valid_updates)
            .execution_options(synchronize_session="fetch")
        )

        await db.execute(stmt)
        await db.commit()

        # Fetch the updated user
        result = await db.execute(select(User).where(cast(User.id == user.id, Boolean)))
        updated_user = result.scalars().first()

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found after update",
            )

        return UserUpdateRequest.from_orm(updated_user)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}",
        )


async def get_user_info(
    commons: dict = Depends(get_common_params),
) -> UserUpdateRequest:  # Changed to UserResponse (see note below)
    user = commons["user"]
    db: AsyncSession = commons["db"]  # Fixed type annotation

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    try:
        # Execute query with eager loading of common relationships
        result = await db.execute(
            select(User)
            .where(User.id == str(user.id))
            .options(
                selectinload(User.profile),  # If you have a profile relationship
                selectinload(User.social_links),  # If you need social links
            )
        )
        user_info = result.scalar_one_or_none()

        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return user_info

    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user information",
        )


async def create_profile(
    commons: dict = Depends(get_common_params),
) -> UserProfileRequest:
    upload_data = commons["update_data"]
    user = commons["user"]
    db: AsyncSession = commons["db"]

    if not upload_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided"
        )

    # Remove user_id if accidentally included
    upload_data.pop("user_id", None)

    try:
        # Check if profile exists and fetch it
        existing_profile = await db.scalar(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )

        if existing_profile:
            # Update only the provided fields (without overwriting others)
            for key, value in upload_data.items():
                if value is not None:  # Optional: Skip None values if you want
                    setattr(existing_profile, key, value)

            await db.commit()
            await db.refresh(existing_profile)
            return UserProfileRequest.model_validate(existing_profile)
        else:
            # Create new profile
            new_profile = UserProfile(user_id=user.id, **upload_data)
            db.add(new_profile)
            await db.commit()
            await db.refresh(new_profile)
            return UserProfileRequest.from_orm(new_profile)

    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )


async def get_profile(
    commons: dict = Depends(get_common_params),
) -> UserProfileRequest:
    user = commons["user"]
    db: AsyncSession = commons["db"]

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,  # More appropriate status code
            detail="Authentication required",
        )

    try:
        result = await db.execute(
            select(UserProfile)
            .where(str(UserProfile.user_id) == str(user.id))
            .options(selectinload(UserProfile.user))
        )  # Eager load user if needed
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,  # More semantically correct
                detail="Profile not found",
            )

        return profile

    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )


async def update_user_settings(
    commons: dict = Depends(get_common_params),
) -> UserSettingsBase:
    update_data = commons["data"]
    user = commons["user"]
    db = commons["db"]

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided"
        )

    # Filter out None values and create update dictionary
    valid_updates = {k: v for k, v in update_data.items() if v != ""}

    # Validate username format
    if not valid_updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update"
        )

    try:
        # Build the update statement
        stmt = (
            update(UserSettings)
            .where(cast(UserSettings.owner_id == user.id, Boolean))
            .values(**valid_updates)
            .execution_options(synchronize_session="fetch")
        )

        await db.execute(stmt)
        await db.commit()

        # Fetch the updated user
        result = await db.execute(
            select(UserSettings).where(cast(UserSettings.owner_id == user.id, Boolean))
        )
        updated_settings = result.scalars().first()

        if not updated_settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Settings not found after update",
            )

        return UserSettingsBase.from_orm(updated_settings)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating settings: {str(e)}",
        )


async def verify_edit_permission(
    project_id: uuid.UUID, user: User, db: AsyncSession
) -> None:
    """Verify user has edit permissions for a project."""
    result = await db.execute(
        select(UserProjectAssociation).filter(
            UserProjectAssociation.user_id == user.id,
            UserProjectAssociation.project_id == project_id,
            UserProjectAssociation.can_edit == True,
        )
    )
    if not result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have edit permissions for this project",
        )


async def get_user_by_username(username: str, db: AsyncSession) -> User:
    """Get user by username with error handling."""
    result = await db.execute(select(User).filter(User.username == username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


def slugify(text: str) -> str:
    # Normalize Unicode characters to ASCII
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove any character that is not alphanumeric, a space, or a hyphen
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    
    # Replace all runs of whitespace or hyphens with a single hyphen
    text = re.sub(r'[\s-]+', '-', text)
    
    # Remove leading and trailing hyphens
    text = text.strip('-')
    
    return text
