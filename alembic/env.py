import asyncio
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine
import os
import sys

# Add your project directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import your Base and models
from app.database import Base
from app.models.db_models import *  # Import all your models

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target_metadata to your Base.metadata
target_metadata = Base.metadata

def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_schemas=True  # Important for schema support
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

if context.is_offline_mode():
    # Handle offline mode if needed
    pass
else:
    asyncio.run(run_migrations_online())