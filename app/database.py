from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Configure connection pool
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,           # Number of permanent connections
    max_overflow=20,        # Number of temporary connections beyond pool_size
    pool_pre_ping=True,     # Test connections for health
    pool_recycle=3600,      # Recycle connections after 1 hour
    pool_timeout=30,        # Wait 30 seconds for a connection
    echo=False             # Set to True for debugging SQL
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Recommended for better session handling
)

Base = declarative_base()

def get_db():
    """Dependency that provides a database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


