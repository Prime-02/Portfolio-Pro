# app/api/ws.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Annotated
# from app.models.db_models import User
from fastapi import APIRouter, Depends
from app.core.security import get_websocket_user
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/ws", tags=["websockets"])

@router.websocket("/chat")
async def websocket_endpoint(
    websocket: WebSocket,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Get user with non-strict authentication (allows anonymous)
    user = await get_websocket_user(websocket, db, strict=False)
    
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            
            if user:
                await websocket.send_text(f"Hello {user.username}! You said: {data}")
            else:
                await websocket.send_text("Hello anonymous! Please authenticate to access features.")
                
    except WebSocketDisconnect:
        pass

