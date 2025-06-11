from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.v1.routers import router as v1_router
from app.database import engine, verify_schema_exists
from app.config import settings
import logging
from app.database import db_middleware
from app.middlewares.middlewares import NotificationAuditMiddleware
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
        lifespan=lifespan
    )
     # Add database middleware FIRST
    app.middleware("http")(db_middleware)
    app.include_router(v1_router, prefix="/api/v1")
    app.add_middleware(NotificationAuditMiddleware)

    @app.get("/")
    async def root():
        return {"message": "Portfolio Pro API"}

    @app.get("/routes")
    async def list_routes():
        return [{"path": route.path, "name": route.name} for route in app.routes]

    return app

app = create_application()