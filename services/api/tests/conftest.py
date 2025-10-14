"""
Pytest configuration and fixtures for ApplyLens API tests.

This module provides:
- Database session fixtures with automatic rollback
- AsyncClient fixture with ASGITransport for httpx>=0.28 compatibility
- Test data factories
- Mock configurations for external services
"""

import asyncio
import os
from typing import AsyncIterator, Generator

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.main import app  # FastAPI instance
from app.models import Base


@pytest.fixture(scope="session")
def anyio_backend():
    """Allow pytest-asyncio/anyio to run httpx async tests."""
    return "asyncio"


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def engine():
    """
    Create a test database engine for the entire test session.

    The database schema is created at the start and dropped at the end.
    Uses DATABASE_URL from environment (set by pytest.ini).

    Note: Tests require PostgreSQL (models use PG-specific types like ARRAY, JSONB, ENUM).
    Set TEST_DB_PASSWORD env var when running locally.
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL not set. Skipping tests that require database.")

    # Create engine with test-friendly settings
    test_engine = create_engine(
        database_url,
        pool_pre_ping=True,
        echo=False,  # Set to True for SQL debugging
        future=True,
    )

    # Create all tables with deferrable constraint handling for circular FKs
    # Use checkfirst to avoid errors if tables exist
    with test_engine.begin() as conn:
        # Set constraints to deferred for circular FK handling
        conn.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        Base.metadata.create_all(conn, checkfirst=True)

    yield test_engine

    # Drop all tables after tests complete
    with test_engine.begin() as conn:
        Base.metadata.drop_all(conn)
    test_engine.dispose()


@pytest.fixture(autouse=True)
def db_session(engine) -> Generator[Session, None, None]:
    """
    Provide a transactional database session for each test.

    Key features:
    - Each test runs in an isolated transaction
    - Changes are automatically rolled back after the test
    - No manual cleanup needed
    - Prevents "multiple rows found" errors from leftover data

    This fixture is autouse=True, so it runs for every test automatically.
    Tests can use the db_session parameter to access the session.
    """
    # Create a connection and begin a transaction
    connection = engine.connect()
    transaction = connection.begin()

    # Create a session bound to this connection
    TestingSessionLocal = sessionmaker(
        bind=connection, autoflush=False, autocommit=False, future=True
    )
    session = TestingSessionLocal()

    # Override the get_db dependency to use our test session
    def override_get_db():
        try:
            yield session
        finally:
            pass  # Don't close here; we'll close in the fixture cleanup

    # Store the override for any code that uses get_db()
    # (You may need to implement dependency override in your app)

    try:
        yield session
    finally:
        session.close()
        # Rollback the transaction - this undoes all changes
        transaction.rollback()
        connection.close()


@pytest.fixture
async def async_client() -> AsyncIterator[httpx.AsyncClient]:
    """
    Provide an async HTTP client for testing FastAPI endpoints.

    Uses ASGITransport for httpx>=0.28 compatibility.
    This replaces the old AsyncClient(app=app, base_url=...) pattern.

    Usage in tests:
        async def test_healthz(async_client):
            response = await async_client.get("/healthz")
            assert response.status_code == 200
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_user_email():
    """Provide a consistent test user email."""
    return "test@example.com"


@pytest.fixture
def clean_user_weights(db_session, sample_user_email):
    """
    Ensure no user weights exist for the test user.

    Use this fixture when you need a clean slate for testing
    weight-related functionality.
    """
    from app.models.personalization import UserWeight

    db_session.query(UserWeight).filter(
        UserWeight.user_id == sample_user_email
    ).delete()
    db_session.commit()

    return sample_user_email


# Add pytest plugins
pytest_plugins = []

# Check for optional pytest plugins
try:
    import pytest_env  # noqa: F401

    pytest_plugins.append("pytest_env")
except ImportError:
    pass

try:
    import pytest_asyncio  # noqa: F401

    pytest_plugins.append("pytest_asyncio")
except ImportError:
    pass


# ============================================================================
# TEST DATA HELPERS
# ============================================================================


@pytest.fixture
def seed_minimal():
    """
    Fixture that returns a function to seed minimal test data.
    
    Creates one application and one email linked to it.
    Useful for tests that need basic data without complex setup.
    
    Usage:
        def test_something(db_session, seed_minimal):
            app, email = seed_minimal(db_session)
            ...
    
    Returns:
        Function that takes a session and returns tuple of (application, email)
    
    Note: Does NOT commit - relies on db_session fixture's automatic rollback.
    """
    def _seed(session: Session):
        from app.models import Application, Email
        
        app = Application(title="SE I", company="Acme", status="applied")
        session.add(app)
        session.flush()
        
        em = Email(subject="hello", sender="hr@acme.com", application_id=app.id)
        session.add(em)
        session.flush()  # Flush but don't commit - db_session handles rollback
        
        return app, em
    
    return _seed
