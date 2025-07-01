from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from fastapi import status
from app.models.db_models import Notification, User
from app.models.schemas import NotificationOut
from app.database import get_websocket_db
import asyncio
import logging
from app.core.security import get_websocket_user
from datetime import datetime
import json

logger = logging.getLogger(__name__)


async def websocket_user_notifications(
    websocket: WebSocket,
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    is_read: Optional[bool] = None,
):
    """WebSocket endpoint for real-time user notifications."""
    user = None

    try:
        logger.info("WebSocket connection accepted")

        # Authenticate user
        user = await get_websocket_user(websocket, db, strict=True)
        if not user:
            logger.warning("User authentication failed")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        logger.info(f"User {user.id} authenticated successfully")

        # Initial notifications fetch
        stmt = select(Notification).where(Notification.user_id == str(user.id))

        if is_read is not None:
            stmt = stmt.where(Notification.is_read == is_read)

        stmt = stmt.offset(skip).limit(limit).order_by(Notification.created_at.desc())

        try:
            result = await db.execute(stmt)
            notifications = result.scalars().all()
            logger.info(f"Found {len(notifications)} initial notifications")
        except SQLAlchemyError as e:
            logger.error(f"Database error: {e}")
            await websocket.close(
                code=status.WS_1011_INTERNAL_ERROR, reason="Database error"
            )
            return

        # Send initial notifications
        if notifications:
            try:
                initial_data = [
                    NotificationOut.model_validate(n, from_attributes=True).model_dump(
                        mode="json"
                    )
                    for n in notifications
                ]

                await websocket.send_json(
                    {
                        "type": "initial_notifications",
                        "data": initial_data,
                        "count": len(initial_data),
                    }
                )
                # Use the most recent notification ID as the last seen
                last_notification_id = notifications[0].id
            except Exception as e:
                logger.error(f"Error sending initial notifications: {e}")
                await websocket.close(
                    code=status.WS_1011_INTERNAL_ERROR, reason="Error sending data"
                )
                return
        else:
            last_notification_id = None
            await websocket.send_json(
                {"type": "initial_notifications", "data": [], "count": 0}
            )

        # Main polling loop
        while True:
            try:
                # Wait for polling interval
                await asyncio.sleep(5)

                # Check for new notifications
                if last_notification_id:
                    new_stmt = select(Notification).where(
                        Notification.user_id == str(user.id),
                        Notification.id > last_notification_id,
                    )
                else:
                    # If no previous notifications, get all notifications
                    new_stmt = select(Notification).where(
                        Notification.user_id == str(user.id)
                    )

                if is_read is not None:
                    new_stmt = new_stmt.where(Notification.is_read == is_read)

                new_stmt = new_stmt.order_by(Notification.created_at.desc())

                new_result = await db.execute(new_stmt)
                new_notifications = new_result.scalars().all()

                if new_notifications:
                    logger.info(
                        f"Found {len(new_notifications)} new notifications for user {user.id}"
                    )

                    # Send each notification individually for real-time feel
                    for notification in new_notifications:
                        notification_data = NotificationOut.model_validate(
                            notification, from_attributes=True
                        ).model_dump(mode="json")

                        await websocket.send_json(
                            {
                                "type": "new_notification",
                                "data": notification_data,
                            }
                        )

                    # Update the last seen notification ID
                    last_notification_id = new_notifications[0].id

                # Send heartbeat to keep connection alive
                await websocket.send_json(
                    {"type": "heartbeat", "timestamp": datetime.now().isoformat()}
                )

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {user.id}")
                break
            except asyncio.CancelledError:
                logger.info(f"WebSocket task cancelled for user {user.id}")
                break
            except SQLAlchemyError as e:
                logger.error(f"Database error in polling: {e}")
                try:
                    await websocket.send_json(
                        {"type": "error", "message": "Database error occurred"}
                    )
                except:
                    pass
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                try:
                    await websocket.send_json(
                        {"type": "error", "message": "Internal server error"}
                    )
                except:
                    pass
                break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected during setup")
    except Exception as e:
        logger.error(f"Unexpected error in websocket handler: {e}")
    finally:
        logger.info(f"Cleaning up connection for user {getattr(user, 'id', 'unknown')}")
        try:
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.close()
        except Exception as e:
            logger.error(f"Error closing websocket: {e}")


async def check_for_new_notifications(
    websocket: WebSocket,
    db: AsyncSession,
    user: User,
    last_notification_id: Optional[str],
    is_read: Optional[bool] = None,
) -> Optional[str]:
    """
    Check for new notifications and send them via WebSocket.
    Returns the new last_notification_id or None if no new notifications.
    """
    try:
        # Build query for new notifications
        if last_notification_id:
            new_stmt = select(Notification).where(
                Notification.user_id == str(user.id),
                Notification.id > last_notification_id,
            )
        else:
            new_stmt = select(Notification).where(Notification.user_id == str(user.id))

        if is_read is not None:
            new_stmt = new_stmt.where(Notification.is_read == is_read)

        new_stmt = new_stmt.order_by(Notification.created_at.desc())

        new_result = await db.execute(new_stmt)
        new_notifications = new_result.scalars().all()

        if new_notifications:
            logger.info(
                f"Found {len(new_notifications)} new notifications for user {user.id}"
            )

            # Convert to output format
            new_data = [
                NotificationOut.model_validate(n, from_attributes=True).model_dump(
                    mode="json"
                )
                for n in new_notifications
            ]

            # Send batch of new notifications
            await websocket.send_json(
                {"type": "new_notifications", "data": new_data, "count": len(new_data)}
            )

            # Return the most recent notification ID
            return new_notifications[0].id

        return last_notification_id

    except SQLAlchemyError as e:
        logger.error(f"Database error checking notifications: {e}")
        raise
    except Exception as e:
        logger.error(f"Error checking for new notifications: {e}")
        raise


async def mark_notification_as_read(
    websocket: WebSocket,
    db: AsyncSession,
    user: User,
    notification_id: str,
) -> bool:
    """
    Mark a notification as read and send confirmation via WebSocket.
    Returns True if successful, False otherwise.
    """
    try:
        # Find the notification
        stmt = select(Notification).where(
            Notification.id == notification_id, Notification.user_id == str(user.id)
        )

        result = await db.execute(stmt)
        notification = result.scalar_one_or_none()

        if not notification:
            await websocket.send_json(
                {"type": "error", "message": "Notification not found"}
            )
            return False

        # Mark as read
        notification.is_read = True
        notification.read_at = datetime.now()

        await db.commit()

        # Send confirmation
        await websocket.send_json(
            {"type": "notification_marked_read", "notification_id": notification_id}
        )

        return True

    except SQLAlchemyError as e:
        logger.error(f"Database error marking notification as read: {e}")
        await db.rollback()
        return False
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        return False
