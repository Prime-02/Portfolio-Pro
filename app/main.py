from fastapi import FastAPI, WebSocket
from contextlib import asynccontextmanager
from app.api.v1.routers import router as v1_router
from app.database import engine, verify_schema_exists
from app.config import settings
import logging
from fastapi.responses import HTMLResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



html = """
<!DOCTYPE html>
<html>
    <head>
        <title>WebSocket Test</title>
    </head>
    <body>
        <h1>WebSocket Test</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            const ws = new WebSocket("ws://localhost:8000/ws");
            ws.onmessage = function(event) {
                const messages = document.getElementById('messages')
                const message = document.createElement('li')
                const content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                const input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""




@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async context manager for application lifespan"""
    # Startup
    if settings.ENVIRONMENT == "development":
        logger.info("Verifying database schema...")
        await verify_schema_exists()
    
    yield
    
    # Shutdown
    logger.info("Closing database connections...")
    await engine.dispose()

def create_application() -> FastAPI:
    app = FastAPI(
        title="Portfolio Pro",
        description="A FastAPI application for managing portfolio projects",
        version="0.1.0",
        lifespan=lifespan
    )
     # Add database middleware FIRST
    app.include_router(v1_router, prefix="/api/v1")

    @app.get("/")
    async def get():
        return HTMLResponse(html)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")

    @app.get("/routes")
    async def list_routes():
        return [{"path": route.path, "name": route.name} for route in app.routes]

    return app

app = create_application()