from typing import Dict, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, insert
from app.models.db_models import User, UserProfile
from app.models.schemas import DBUser, UserProfileRequest
from app.core.security import get_current_user
from fastapi import HTTPException, status, Depends
from sqlalchemy import Boolean, cast
from app.database import get_db
from app.core.security import validate_username
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.expression import exists


async def get_common_params(
    data: Dict[str, Union[str, bool]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": data, "user": user, "db": db}


async def update_user_info(
    commons: dict = Depends(get_common_params),
) -> DBUser:
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

        return DBUser.model_validate(updated_user)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}",
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
            return UserProfileRequest.from_orm(existing_profile)
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
