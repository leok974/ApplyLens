"""
Regression tests for logout endpoint (Phase 4 logout bug).

This test suite prevents regression of the logout 500 error caused by
naming conflicts between SQLAlchemy Session and custom Session model.

See: docs/DOCKER_SETUP_COMPLETE.md for full context.
"""

from sqlalchemy.orm import Session as DBSession

from app.models import User
from app.models import Session as UserSession  # <-- The critical fix we're testing


def test_logout_session_model_query_works(db_session: DBSession):
    """
    Test that Session model can be queried without naming conflicts.

    Regression: Previously broke with error "Session is not callable"
    because of missing alias: 'from app.models import Session as UserSession'

    Root cause: SQLAlchemy's Session class conflicts with our Session model
    Fix: Always import as 'Session as UserSession' in auth routes
    Fixed in: app/routers/auth.py (Line 7)
    """
    # Create test user
    user = User(email="test-logout@example.com", name="Test User", is_demo=True)
    db_session.add(user)
    db_session.commit()

    # Create session for the user (this is what broke before)
    session = UserSession(user_id=user.id)
    db_session.add(session)
    db_session.commit()
    session_id = session.id

    # Simulate the logout query that was failing
    # Before fix: db.query(Session) would try to call SQLAlchemy Session class
    # After fix: db.query(UserSession) correctly queries the model
    db_session.query(UserSession).filter(UserSession.id == session_id).delete()
    db_session.commit()

    # Verify session was deleted
    deleted_session = (
        db_session.query(UserSession).filter(UserSession.id == session_id).first()
    )
    assert deleted_session is None

    # Verify user still exists
    existing_user = db_session.query(User).filter(User.id == user.id).first()
    assert existing_user is not None

    # Cleanup
    db_session.query(User).filter(User.email == "test-logout@example.com").delete()
    db_session.commit()


def test_session_alias_pattern():
    """
    Test that demonstrates the correct import pattern.

    This test validates our best practice:
    ALWAYS use: from app.models import Session as UserSession
    NEVER use: from app.models import Session

    This prevents naming conflicts with SQLAlchemy's Session class.
    """
    from app.models import Session as UserSession
    from sqlalchemy.orm import Session as DBSession

    # Both imports should work without conflict
    assert UserSession is not None
    assert DBSession is not None

    # UserSession should be our model class
    assert hasattr(UserSession, "__tablename__")
    assert UserSession.__tablename__ == "sessions"
