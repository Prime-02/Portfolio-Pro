from typing import Optional, Union, Dict
from uuid import UUID
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from fastapi import HTTPException, status, Depends
from app.models.db_models import Notification, User
from app.models.schemas import NotificationCreate, NotificationUpdate, NotificationOut
from datetime import datetime
from app.database import get_db
from app.core.security import get_current_user


async def get_common_params(
    data: Dict[str, Union[str, bool, datetime]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": data, "user": user, "db": db}


async def create_notification(
    commons: dict = Depends(get_common_params),
) -> NotificationOut:
    """
    Create a new notification for the authenticated user.
    Raises 422 if input validation fails, 500 on DB errors.
    """
    notification_data = commons["data"]
    user = commons["user"]
    db: AsyncSession = commons["db"]
    
    try:
        # Ensure the notification is created for the authenticated user
        notification_dict = dict(notification_data)
        notification_dict["user_id"] = user.id
        
        db_notification = Notification(**notification_dict)
        db.add(db_notification)
        await db.commit()
        await db.refresh(db_notification)
        return db_notification
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification: {str(e)}",
        )


async def update_notification(
    notification_id: UUID,
    update_data: NotificationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationOut:
    """
    Update a notification (e.g., mark as read) for the authenticated user.
    Raises 404 if not found or not owned by user, 500 on DB errors.
    """
    try:
        # Query notification and ensure it belongs to the authenticated user
        result = await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user.id
            )
        )
        db_notification = result.scalar_one_or_none()

        if not db_notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Notification not found or access denied"
            )

        # Update fields
        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(db_notification, field, value)

        # Set read_at timestamp when marking as read
        if update_data.is_read and not db_notification.read_at:
            db_notification.read_at = datetime.utcnow()

        await db.commit()
        await db.refresh(db_notification)
        return db_notification
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update notification: {str(e)}",
        )


async def delete_notification(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> bool:
    """
    Delete a notification for the authenticated user.
    Returns True if successful, False if not found.
    """
    try:
        # Query notification and ensure it belongs to the authenticated user
        result = await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user.id
            )
        )
        db_notification = result.scalar_one_or_none()

        if not db_notification:
            return False

        await db.delete(db_notification)
        await db.commit()
        return True
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete notification: {str(e)}",
        )


async def mark_all_as_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> int:
    """Mark all notifications as read for the authenticated user. Returns count updated."""
    try:
        # Use the authenticated user's ID
        stmt = (
            update(Notification)
            .where(Notification.user_id == user.id, Notification.is_read == False)
            .values(is_read=True, read_at=datetime.utcnow())
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount or 0
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk update notifications: {str(e)}",
        )


async def delete_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> int:
    """Delete all read notifications for the authenticated user. Returns count deleted."""
    try:
        # Use the authenticated user's ID
        stmt = delete(Notification).where(
            Notification.user_id == user.id, 
            Notification.is_read == True
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount or 0
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk delete notifications: {str(e)}",
        )


async def get_notification_with_relations(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Optional[dict]:
    """
    Fetch a notification with resolved relationships for the authenticated user.
    Returns None if not found or not owned by user.
    """
    try:
        # Query notification and ensure it belongs to the authenticated user
        result = await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user.id
            )
        )
        notification = result.scalar_one_or_none()

        if not notification:
            return None

        notification_dict = {
            **notification.__dict__,
            "actor": None,
            "related_entity": None,
        }

        # Resolve actor (example)
        if notification.actor_id:
            actor_result = await db.execute(
                select(User).where(User.id == notification.actor_id)
            )
            actor = actor_result.scalar_one_or_none()
            notification_dict["actor"] = (
                {"id": actor.id, "username": actor.username} if actor else None
            )

        return notification_dict
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch notification with relations: {str(e)}",
        )


async def get_user_notifications(
    skip: int = 0,
    limit: int = 100,
    is_read: Optional[bool] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationOut]:
    """
    Get all notifications for the authenticated user with pagination and read status filter.

    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        is_read: Optional filter for read/unread notifications
        user: Authenticated user (injected by dependency)
        db: Database AsyncSession (injected by dependency)

    Returns:
        List of NotificationOut objects for the authenticated user
    """
    try:
        # Build query using the authenticated user's ID
        stmt = select(Notification).where(Notification.user_id == user.id)

        if is_read is not None:
            stmt = stmt.where(Notification.is_read == is_read)

        stmt = stmt.offset(skip).limit(limit).order_by(Notification.created_at.desc())

        result = await db.execute(stmt)
        notifications = result.scalars().all()
        return notifications
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch notifications: {str(e)}",
        )