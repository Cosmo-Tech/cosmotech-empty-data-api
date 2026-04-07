import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from cosmotech.example_api.schema.model import SQLModel
from cosmotech.example_api.utils.config import Configuration

# Import all model modules to ensure they're registered with SQLModel.metadata
# Using module imports instead of class imports to avoid unused import warnings
# while still triggering model registration


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# NOTE: Logging configuration is NOT loaded from alembic.ini to avoid
# interfering with the application's logger configuration.
# The application's main logger (`uvicorn.error`) manages all logging.

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    """Get database URL from configuration."""
    config_path = os.environ.get("CONFIG_PATH", "config.toml")
    try:
        _config = Configuration(config_path)
        url = _config.psql_uri
        # Set search path if schema is specified
        if hasattr(_config, "psql_schema") and _config.psql_schema:
            connect_args = {"options": f"-csearch_path={_config.psql_schema}"}
        else:
            connect_args = {}
        return url, connect_args
    except (AttributeError, FileNotFoundError):
        # Fallback to SQLite
        data_dir = os.environ.get("DATA_DIR", "./data")
        sqlite_file_name = os.path.join(data_dir, "database.db")
        return f"sqlite:///{os.path.abspath(sqlite_file_name)}", {}


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url, _ = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    url, connect_args = get_url()

    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
