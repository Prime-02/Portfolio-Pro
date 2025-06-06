from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "My FastAPI App"
    admin_email: str  # Required field
    items_per_user: int = 50
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    DB_SCHEMA: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GMAIL_REFRESH_TOKEN: str
    MAIL_DEFAULT_SENDER: str
    ENVIRONMENT: str = "development"  # Default to development

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
