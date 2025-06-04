from fastapi import FastAPI
from app.api.v1.routers import router as v1_router



def create_application() -> FastAPI:
    app = FastAPI(
        title="Portfolio Pro",
        description="A FastAPI application for managing portfolio projects",
        # dependencies=[
        #     Depends(get_query_token)
        # ],  # Optional: if you have global dependencies
    )

    app.include_router(v1_router, prefix="/api/v1")

    # Include your routes
    @app.get("/")
    async def root():
        return {"yoo": "Hello World"}

    return app


app = create_application()
