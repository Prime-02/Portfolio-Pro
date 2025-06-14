from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware  # <-- Add this import
from contextlib import asynccontextmanager
from app.api.v1.routers import router as v1_router
from app.database import engine, verify_schema_exists
from app.config import settings
import logging
from fastapi.responses import HTMLResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        lifespan=lifespan,
    )

    # ===== CORS Configuration =====
    origins = [
        "*",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://your-production-domain.com",
    ]

    # Add CORS middleware (MUST be before routers)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,  # Allows cookies/sessions
        allow_methods=["*"], 
        allow_headers=["*"], 
    )

    # Include routers AFTER CORS middleware
    app.include_router(v1_router, prefix="/api/v1")

    @app.get("/routes")
    async def list_routes():
        return [{"path": route.path, "name": route.name} for route in app.routes]

    return app


app = create_application()
