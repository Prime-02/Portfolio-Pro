from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from uuid import UUID
from typing import Optional
from datetime import datetime
from app.models.db_models import Notification, User
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import NotificationUpdate, NotificationOut, NotificationCreate
from app.database import get_db
from app.core.security import get_current_user
from app.core.corenotification import (
    create_notification,
    update_notification,
    delete_notification,
    mark_all_as_read,
    delete_all_read,
    get_notification_with_relations,
    get_user_notifications,
    get_common_params,
)
from fastapi import Query


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post(
    "/",
    response_model=NotificationOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Notification created successfully"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)
async def create_notification_endpoint(
    notification_data: NotificationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> NotificationOut:
    """
    Create a new notification for the authenticated user.
    """
    # Convert Pydantic model to dict for the common params
    commons = await get_common_params(
        data=notification_data.model_dump(),
        user=user,
        db=db
    )
    return await create_notification(commons)


@router.get("/{notification_id}", response_model=dict)
async def get_notification(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific notification with its relationships for the authenticated user.
    """
    notification = await get_notification_with_relations(
        notification_id=notification_id,
        user=user,
        db=db
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied"
        )
    return notification


@router.patch("/{notification_id}", response_model=NotificationOut)
async def update_notification_endpoint(
    notification_id: UUID,
    update_data: NotificationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a notification (e.g., mark as read) for the authenticated user.
    """
    return await update_notification(
        notification_id=notification_id,
        update_data=update_data,
        user=user,
        db=db
    )


@router.delete("/{notification_id}")
async def delete_notification_endpoint(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a notification for the authenticated user.
    Returns 204 if successful, 404 if not found.
    """
    success = await delete_notification(
        notification_id=notification_id,
        user=user,
        db=db
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied"
        )
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


@router.post("/mark-all-as-read")
async def mark_all_as_read_endpoint(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark all notifications for the authenticated user as read.
    Returns count of updated notifications.
    """
    count = await mark_all_as_read(user=user, db=db)
    return {"count": count, "message": f"Marked {count} notifications as read"}


@router.delete("/delete-read")
async def delete_all_read_endpoint(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete all read notifications for the authenticated user.
    Returns count of deleted notifications.
    """
    count = await delete_all_read(user=user, db=db)
    return {"count": count, "message": f"Deleted {count} read notifications"}


@router.get("/", response_model=list[NotificationOut])
async def get_user_notifications_endpoint(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, le=1000, description="Pagination limit"),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all notifications for the authenticated user.

    Parameters:
    - skip: Number of notifications to skip (for pagination)
    - limit: Maximum number of notifications to return
    - is_read: Optional filter for read/unread notifications

    Returns:
    - List of notifications for the authenticated user
    """
    notifications = await get_user_notifications(
        skip=skip,
        limit=limit,
        is_read=is_read,
        user=user,
        db=db
    )
    return notifications


@router.get("/unread/count")
async def get_unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get count of unread notifications for the authenticated user.
    """
    notifications = await get_user_notifications(
        skip=0,
        limit=1000,  # Get a large number to count
        is_read=False,
        user=user,
        db=db
    )
    return {"unread_count": len(notifications)}