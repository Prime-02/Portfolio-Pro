from typing import Dict, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from app.models.db_models import User
from app.models.schemas import DBUser
from app.core.security import get_current_user
from fastapi import HTTPException, status, Depends
from sqlalchemy import Boolean, cast
from app.database import get_db


async def update_user_info(
    update_data: Dict[str, Union[str, bool]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DBUser:
    """Update user information in the database."""
    print("Updating user info:", update_data)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided"
        )

    # Filter out None values and create update dictionary
    valid_updates = {k: v for k, v in update_data.items() if v != ""}

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
