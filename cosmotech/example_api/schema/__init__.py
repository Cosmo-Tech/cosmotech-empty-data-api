import os
from typing import Annotated

from alembic.script.revision import ResolutionError
from fastapi import Depends
from sqlmodel import Session

from cosmotech.example_api.schema.model import SQLModel
from cosmotech.example_api.utils.config import Configuration
from cosmotech.example_api.utils.logging import LOGGER

from .api_usage import ApiUsage

engines = []


def initialize_tables():
    """Initialize database tables using Alembic migrations."""
    engine = engines[0]
    _config_path = os.environ.get("CONFIG_PATH", "config.toml")

    try:
        _config = Configuration(_config_path)
        database_reset = _config.database_reset
        use_sqlite = not _config.use_psql
    except (AttributeError, FileNotFoundError):
        database_reset = False
        use_sqlite = True

    if database_reset:
        LOGGER.warning("Database reset enabled - dropping all tables")
        SQLModel.metadata.drop_all(engine)
        LOGGER.debug("All tables dropped")

    if use_sqlite:
        SQLModel.metadata.create_all(engine)

    # Use Alembic migrations for schema management
    try:
        from cosmotech.example_api.migrations import run_migrations

        LOGGER.info("Running database migrations")
        # auto_generate=False for production safety
        # Set to True only in development if you want automatic migration generation
        auto_generate = os.environ.get("AUTO_GENERATE_MIGRATIONS", "false").lower() == "true"
        run_migrations(engine, auto_generate=auto_generate)
        LOGGER.info("Database initialization completed")

    except ImportError as e:
        # Alembic not installed - only acceptable in development/testing
        LOGGER.warning(
            f"Alembic not available ({e}). Using fallback create_all() method. "
            "This is only suitable for development/testing environments."
        )
        LOGGER.debug("Creating tables with SQLModel.metadata.create_all()")
        SQLModel.metadata.create_all(engine)
    except ResolutionError as e:
        LOGGER.warning(f"Alembic migration failed due to missing revision: {e.argument}. Trusting current schema.")
    except Exception as e:
        # Migration failed - this is a serious error that should not be silently ignored
        LOGGER.error(
            f"Database migration failed: {e}. "
            "This could indicate schema inconsistencies or migration conflicts. "
            "Please review the error and fix the migration before proceeding."
        )
        # Re-raise the exception to fail fast rather than creating inconsistent state
        # If you need to use create_all() as a fallback in specific cases, set:
        # ALLOW_MIGRATION_FALLBACK=true environment variable (not recommended for production)
        allow_fallback = os.environ.get("ALLOW_MIGRATION_FALLBACK", "false").lower() == "true"
        if allow_fallback:
            LOGGER.warning(
                "ALLOW_MIGRATION_FALLBACK is enabled. Using create_all() as fallback. "
                "WARNING: This may create schema inconsistencies!"
            )
            SQLModel.metadata.create_all(engine)
        else:
            LOGGER.critical("Migration failed and fallback is disabled. Application cannot start safely.")
            raise


def add_engine(engine):
    engines.append(engine)


def get_session():
    with Session(engines[0]) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
