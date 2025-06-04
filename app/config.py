from pydantic_settings import BaseSettings
import os

print("Current working directory:", os.getcwd())
print("Environment variables:", os.environ.get("ADMIN_EMAIL"))


class Settings(BaseSettings):
    app_name: str = "My FastAPI App"
    admin_email: str  # Required field
    items_per_user: int = 50
    DATABASE_URL: str = (
        "postgresql://portfolio_pro_user:portfolio_pro_user@localhost:5432/portfolio_pro_db?sslmode=disable"
    )
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    DB_SCHEMA: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
print("Loaded settings:", settings.model_dump())
