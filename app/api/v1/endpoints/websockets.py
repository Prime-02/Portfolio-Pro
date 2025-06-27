from fastapi import WebSocket, WebSocketDisconnect
from typing import Optional, Annotated
from app.models.db_models import User
from fastapi import APIRouter, Depends
from app.core.security import get_websocket_user

router = APIRouter(prefix="/ws", tags=["websockets"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user: Annotated[Optional[User], Depends(get_websocket_user)],
):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # Process data with authenticated user
            await websocket.send_text(f"Hello {user.username if user else 'anonymous'}")
    except WebSocketDisconnect:
        # Connection was closed (either by client or due to auth failure)
        pass
    