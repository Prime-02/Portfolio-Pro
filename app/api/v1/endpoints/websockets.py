# app/api/ws.py
from fastapi import WebSocket, WebSocketDisconnect, status
from typing import Annotated
from fastapi import APIRouter, Depends
from app.core.security import get_websocket_user
from app.database import get_websocket_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.websocketscore.notification import (
    websocket_user_notifications,
    check_for_new_notifications,
)
from urllib.parse import parse_qs
import logging
import asyncio


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["websockets"])


@router.websocket("/chat")
async def websocket_endpoint(
    websocket: WebSocket,
    db: Annotated[AsyncSession, Depends(get_websocket_db)],
):
    # Get user with non-strict authentication (allows anonymous)
    user = await get_websocket_user(websocket, db, strict=False)

    try:
        while True:
            data = await websocket.receive_text()

            if user:
                await websocket.send_text(f"Hello {user.username}! You said: {data}")
            else:
                await websocket.send_text(
                    "Hello anonymous! Please authenticate to access features."
                )

    except WebSocketDisconnect:
        pass
    finally:
        await db.close()  # Important: Manually close the session


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
):
    async with get_websocket_db() as db:
        try:
            await websocket.accept()  # Accept the connection first

            # Parse query parameters from WebSocket URL
            query_params = parse_qs(websocket.url.query) if websocket.url.query else {}

            # Extract parameters with defaults and validation
            try:
                skip = int(query_params.get("skip", [0])[0])
                limit = int(query_params.get("limit", [100])[0])
                is_read_param = query_params.get("is_read", [None])[0]

                # Convert is_read to boolean if provided
                is_read = False
                if is_read_param is not None:
                    is_read = is_read_param.lower() in ("true", "1", "yes")

                # Validate parameters
                skip = max(0, skip)  # Ensure skip is not negative
                limit = min(max(1, limit), 1000)  # Ensure limit is between 1 and 1000

            except (ValueError, IndexError, TypeError) as e:
                logger.error(f"Invalid query parameters: {e}")
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Invalid query parameters",
                )
                return

            logger.info(
                f"WebSocket connection with params: skip={skip}, limit={limit}, is_read={is_read}"
            )

            # Call the function with proper parameters (remove the user parameter)
            await websocket_user_notifications(
                websocket=websocket, db=db, skip=skip, limit=limit, is_read=is_read
            )

        except WebSocketDisconnect:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"Error: {e}")
            try:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            except:
                pass  # Connection might already be closed


@router.websocket("/notifications/updates")
async def websocket_notification_updates(
    websocket: WebSocket,
):
    async with get_websocket_db() as db:
        try:
            await websocket.accept()

            # Get authenticated user (strict=True for protected endpoint)
            user = await get_websocket_user(websocket, db, strict=True)
            if not user:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

            # Get last_notification_id from query params
            query_params = parse_qs(websocket.url.query) if websocket.url.query else {}
            last_notification_id = query_params.get("last_id", [None])[0]

            # Optional is_read filter
            is_read_param = query_params.get("is_read", [None])[0]
            is_read = False
            if is_read_param is not None:
                is_read = is_read_param.lower() in ("true", "1", "yes")

            logger.info(
                f"Notification updates connection for user {user.id} "
                f"(last_id: {last_notification_id}, is_read: {is_read})"
            )

            while True:
                # Check for new notifications
                last_notification_id = await check_for_new_notifications(
                    websocket=websocket,
                    db=db,
                    user=user,
                    last_notification_id=last_notification_id,
                    is_read=is_read,
                )

                # Wait before next check
                await asyncio.sleep(5)  # Adjust polling interval as needed

        except WebSocketDisconnect:
            logger.info(f"User {user.id} disconnected from updates")
        except Exception as e:
            logger.error(f"Notification updates error: {e}")
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

