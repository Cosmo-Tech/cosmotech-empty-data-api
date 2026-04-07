"""
Shared test fixtures and configuration for the Asset Investment Planning API tests.

This module provides:
- Test database setup (in-memory SQLite)
- FastAPI TestClient configuration
- Authentication mocking
- Common test data factories
"""

import os
from datetime import datetime, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

# Set test environment variables before importing the app
os.environ["KEYCLOAK_REALM"] = "test-realm"
os.environ["DATA_DIR"] = "./test_data"

from cosmotech.example_api.__main__ import app
from cosmotech.example_api.schema import SessionDep, add_engine, engines
from cosmotech.example_api.utils.oauth2 import valid_access_token


@pytest.fixture(name="engine")
def engine_fixture():
    """Create an in-memory SQLite engine for testing."""
    from sqlalchemy import event

    # Clear any existing engines to ensure test isolation
    engines.clear()

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign key constraint enforcement in SQLite and register custom math functions
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=OFF")  # Faster writes for tests
        cursor.execute("PRAGMA journal_mode=MEMORY")  # Keep journal in memory
        cursor.close()
        # Register power() so the KPI views can use it (SQLite does not expose
        # math functions unless compiled with SQLITE_ENABLE_MATH_FUNCTIONS)
        dbapi_connection.create_function("power", 2, lambda x, y: x**y)

    # Create tables and KPI views (views require tables to exist first)
    SQLModel.metadata.create_all(engine)
    with engine.connect() as conn:
        from cosmotech.example_api.utils.views import create_kpi_views_sqlite

        create_kpi_views_sqlite(conn.connection)
    add_engine(engine)

    yield engine

    # Cleanup: Dispose of the engine to close all connections
    engine.dispose()
    engines.clear()


@pytest.fixture(name="session")
def session_fixture(engine) -> Generator[Session, None, None]:
    """Create a new database session for each test."""
    with Session(engine) as session:
        yield session
        # Ensure session is properly closed
        session.close()


@pytest.fixture(scope="function")
def postgres_api_engine():
    """PostgreSQL engine for API tests (tables + KPI views created fresh for each test).

    Skips automatically when the PostgreSQL test database is unavailable.
    Start it with: docker-compose -f docker-compose.test.yml up -d
    """
    from sqlalchemy import create_engine as pg_create_engine
    from sqlalchemy import event, text
    from sqlmodel import SQLModel

    from cosmotech.example_api.schema import add_engine, engines
    from cosmotech.example_api.utils.config import Configuration

    os.environ["CONFIG_PATH"] = "config.test.toml"

    try:
        config = Configuration("config.test.toml")
        probe = pg_create_engine(config.psql_uri, pool_pre_ping=True)
        with probe.connect() as conn:
            conn.execute(text("SELECT 1"))
        probe.dispose()
    except Exception:
        pytest.skip(
            "PostgreSQL test database is not available. "
            "Start it with: docker-compose -f docker-compose.test.yml up -d"
        )

    engines.clear()
    engine = pg_create_engine(config.psql_uri, pool_pre_ping=True)

    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO test_user"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        conn.commit()

    SQLModel.metadata.create_all(engine)

    add_engine(engine)

    yield engine

    engine.dispose()
    engines.clear()


@pytest.fixture(scope="function")
def postgres_api_session(postgres_api_engine) -> Generator[Session, None, None]:
    """Database session backed by the PostgreSQL API engine."""
    with Session(postgres_api_engine) as session:
        yield session
        session.close()


@pytest.fixture(name="client")
def client_fixture(request) -> Generator[TestClient, None, None]:
    """Create a FastAPI TestClient with mocked authentication.

    Backend selection is driven by pytest marks on the requesting test:

    * **No mark** (default): SQLite in-memory via the ``session`` fixture.
    * **@pytest.mark.requires_postgres**: PostgreSQL via ``postgres_api_session``.
      The test is automatically skipped when the PostgreSQL database is unavailable.
    """
    if request.node.get_closest_marker("requires_postgres"):
        session = request.getfixturevalue("postgres_api_session")
    else:
        session = request.getfixturevalue("session")

    def get_session_override():
        return session

    # Mock the authentication dependency
    def mock_valid_access_token():
        return {
            "sub": "test-user-id",
            "name": "Test User",
            "email": "test@example.com",
            "preferred_username": "testuser",
        }

    app.dependency_overrides[SessionDep] = get_session_override
    app.dependency_overrides[valid_access_token] = mock_valid_access_token

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_token():
    """Provide a mock authentication token dictionary."""
    return {
        "sub": "test-user-id",
        "name": "Test User",
        "email": "test@example.com",
        "preferred_username": "testuser",
    }


@pytest.fixture
def utc_now():
    """Provide current UTC time for testing."""
    return datetime.now(timezone.utc)
