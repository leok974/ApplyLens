"""
Pytest configuration and fixtures for ApplyLens API tests.

This module provides:
- Database session fixtures with automatic rollback
- Test data factories
- Mock configurations for external services
"""

import os
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.models import Base
from app.db import get_db


@pytest.fixture(scope="session")
def engine():
    """
    Create a test database engine for the entire test session.
    
    The database schema is created at the start and dropped at the end.
    Uses DATABASE_URL from environment (set by pytest.ini).
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.fail("DATABASE_URL not set. Run tests with TEST_DB_PASSWORD environment variable.")
    
    # Create engine with test-friendly settings
    test_engine = create_engine(
        database_url,
        pool_pre_ping=True,
        echo=False,  # Set to True for SQL debugging
        future=True
    )
    
    # Create all tables
    Base.metadata.create_all(test_engine)
    
    yield test_engine
    
    # Drop all tables after tests complete
    Base.metadata.drop_all(test_engine)
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
        bind=connection,
        autoflush=False,
        autocommit=False,
        future=True
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
    import pytest_env
    pytest_plugins.append('pytest_env')
except ImportError:
    pass

try:
    import pytest_asyncio
    pytest_plugins.append('pytest_asyncio')
except ImportError:
    pass
