"""Database migration utilities using Alembic."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect

from cosmotech.example_api.utils.logging import LOGGER


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    # Try to locate alembic.ini in a robust way:
    # 1. Check the current working directory (typical for CLI usage).
    # 2. Walk up the directory tree from this file, looking for alembic.ini.
    alembic_ini_path = Path.cwd() / "alembic.ini"

    if not alembic_ini_path.exists():
        for parent in Path(__file__).resolve().parents:
            candidate = parent / "alembic.ini"
            if candidate.exists():
                alembic_ini_path = candidate
                break
        else:
            raise FileNotFoundError("Alembic configuration file 'alembic.ini' could not be found.")

    alembic_cfg = Config(str(alembic_ini_path))
    return alembic_cfg


def run_migrations(engine: Engine, auto_generate: bool = False) -> None:
    """
    Run database migrations.

    Args:
        engine: SQLAlchemy engine instance
        auto_generate: If True, auto-generate migration if schema changed
    """
    alembic_cfg = get_alembic_config()

    # Check if database has any tables
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # Check if alembic_version table exists
    has_alembic_version = "alembic_version" in existing_tables

    if not has_alembic_version and not existing_tables:
        # Fresh database - create initial migration and stamp it
        LOGGER.info("Fresh database detected - initializing Alembic")
        try:
            # Check if migrations exist
            migrations_dir = Path(alembic_cfg.get_main_option("script_location")) / "versions"
            if migrations_dir.exists() and list(migrations_dir.glob("*.py")):
                LOGGER.info("Existing migrations found - applying them")
                command.upgrade(alembic_cfg, "head")
            else:
                LOGGER.info("No migrations found - creating initial migration")
                command.revision(alembic_cfg, autogenerate=True, message="Initial schema")
                command.upgrade(alembic_cfg, "head")
        except Exception as e:
            LOGGER.error(f"Error during initial migration: {e}")
            raise

    elif not has_alembic_version and existing_tables:
        # Database exists but no Alembic - stamp current version
        LOGGER.info("Existing database without Alembic detected - stamping current version")
        try:
            # Check if initial migration exists
            migrations_dir = Path(alembic_cfg.get_main_option("script_location")) / "versions"
            if not migrations_dir.exists() or not list(migrations_dir.glob("*.py")):
                LOGGER.info("Creating initial migration from existing schema")
                command.revision(alembic_cfg, autogenerate=True, message="Initial schema from existing database")
            command.stamp(alembic_cfg, "head")
            LOGGER.info("Database stamped with current migration version")
        except Exception as e:
            LOGGER.error(f"Error stamping database: {e}")
            raise

    else:
        # Normal case - run pending migrations
        LOGGER.info("Checking for pending migrations")
        try:
            if auto_generate:
                # Check if schema changed and auto-generate migration
                LOGGER.debug("Checking for schema changes to auto-generate migration")
                from alembic.autogenerate import compare_metadata
                from alembic.runtime.migration import MigrationContext

                from cosmotech.example_api.schema.model import SQLModel

                # Compare current schema with database
                with engine.connect() as conn:
                    mc = MigrationContext.configure(conn)
                    diff = compare_metadata(mc, SQLModel.metadata)

                if diff:
                    LOGGER.info("Schema changes detected - generating migration")
                    command.revision(alembic_cfg, autogenerate=True, message="Auto-generated schema update")
                else:
                    LOGGER.debug("No schema changes detected - skipping auto-generation")

            # Apply pending migrations
            command.upgrade(alembic_cfg, "head")
            LOGGER.info("Database migrations completed successfully")
        except Exception as e:
            LOGGER.error(f"Error during migration: {e}")
            raise


def create_migration(message: str) -> None:
    """
    Create a new migration.

    Args:
        message: Migration message/description
    """
    alembic_cfg = get_alembic_config()
    command.revision(alembic_cfg, autogenerate=True, message=message)
    LOGGER.info(f"Migration created: {message}")


def downgrade_migration(revision: str = "-1") -> None:
    """
    Downgrade to a specific revision.

    Args:
        revision: Target revision (default: -1 for previous)
    """
    alembic_cfg = get_alembic_config()
    command.downgrade(alembic_cfg, revision)
    LOGGER.info(f"Downgraded to revision: {revision}")
