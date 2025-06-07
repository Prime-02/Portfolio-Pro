from typing import Dict, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, insert
from app.models.db_models import User, UserProfile
from app.models.schemas import (
    DBUser,
    UserProfileRequest,
    UserUpdateRequest,
    UserUpdateRequest,
)
from app.core.security import get_current_user
from fastapi import HTTPException, status, Depends
from sqlalchemy import Boolean, cast
from app.database import get_db
from app.core.security import validate_username
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload


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
            .where(User.id == user.id)
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
            .where(UserProfile.user_id == user.id)
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
