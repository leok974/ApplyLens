"""Tests for resume upload and management endpoints."""

import io
import os

# Disable CSRF for tests
os.environ["CSRF_ENABLED"] = "false"

from fastapi.testclient import TestClient
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    JSON,
    Text,
    event,
)
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

from app.main import app
from app.db import get_db
from app.models import ResumeProfile  # Import production model

# Minimal ResumeProfile model for testing (SQLite compatible)
TestBase = declarative_base()


class TestResumeProfile(TestBase):
    """Test-only ResumeProfile model without ARRAY types."""

    __tablename__ = "resume_profiles"

    id = Column(Integer, primary_key=True)
    owner_email = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    raw_text = Column(Text)  # Add missing column from production model
    headline = Column(String)
    summary = Column(Text)
    skills = Column(JSON)  # JSON instead of ARRAY for SQLite
    experiences = Column(JSON)
    projects = Column(JSON)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


# Add listeners to PRODUCTION model to auto-populate timestamps
@event.listens_for(ResumeProfile, "before_insert")
def set_resume_created_updated(mapper, connection, target):
    """Set created_at and updated_at before insert (for tests)."""
    now = datetime.utcnow()
    if target.created_at is None:
        target.created_at = now
    if target.updated_at is None:
        target.updated_at = now


@event.listens_for(ResumeProfile, "before_update")
def set_resume_updated(mapper, connection, target):
    """Set updated_at before update (for tests)."""
    target.updated_at = datetime.utcnow()


# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_resume.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test tables
TestBase.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_upload_resume_txt():
    """Test uploading a .txt resume file."""
    # Create a simple text resume
    resume_content = """
John Doe
Software Engineer

SUMMARY
Experienced software engineer with 5 years in Python and web development.

SKILLS
Python, FastAPI, React, PostgreSQL, Docker

EXPERIENCE
Senior Developer at TechCorp (2020-2025)
- Built scalable web applications
- Led team of 3 developers

PROJECTS
- E-commerce platform using FastAPI
- Real-time chat application
"""

    # Create file-like object
    file_data = io.BytesIO(resume_content.encode())

    # Upload resume
    response = client.post(
        "/api/resume/upload",
        files={"file": ("resume.txt", file_data, "text/plain")},
        headers={
            "X-User-Email": "test@applylens.com",
            "Authorization": "Bearer test-token",  # Use M2M auth to bypass CSRF
        },
    )

    assert response.status_code == 201, f"Upload failed: {response.text}"
    data = response.json()

    # Verify response structure
    assert "id" in data
    assert data["owner_email"] == "test@applylens.com"
    assert data["source"] == "upload"  # Source is always 'upload' for uploaded resumes
    assert data["is_active"] is True

    # Verify profile was created in database
    db = TestingSessionLocal()
    try:
        profile = (
            db.query(TestResumeProfile)
            .filter_by(owner_email="test@applylens.com")
            .first()
        )

        assert profile is not None, "Resume profile not found in database"
        assert profile.is_active is True
        assert profile.source == "upload"
    finally:
        db.close()


def test_get_current_resume():
    """Test retrieving current active resume."""
    # Upload a resume first
    resume_content = "John Doe - Software Engineer"
    file_data = io.BytesIO(resume_content.encode())

    upload_response = client.post(
        "/api/resume/upload",
        files={"file": ("my_resume.txt", file_data, "text/plain")},
        headers={
            "X-User-Email": "current@test.com",
            "Authorization": "Bearer test-token",
        },
    )
    assert upload_response.status_code == 201

    # Get current resume
    response = client.get(
        "/api/resume/current", headers={"X-User-Email": "current@test.com"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data is not None
    assert data["owner_email"] == "current@test.com"
    assert data["source"] == "upload"
    assert data["is_active"] is True


def test_get_current_resume_no_resume():
    """Test /current returns null when no resume exists."""
    response = client.get(
        "/api/resume/current", headers={"X-User-Email": "nouser@test.com"}
    )

    assert response.status_code == 200
    assert response.json() is None


def test_upload_resume_invalid_format():
    """Test uploading unsupported file format returns 400."""
    file_data = io.BytesIO(b"fake image data")

    response = client.post(
        "/api/resume/upload",
        files={"file": ("resume.png", file_data, "image/png")},
        headers={
            "X-User-Email": "test@applylens.com",
            "Authorization": "Bearer test-token",
        },
    )

    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


# Cleanup
def teardown_module():
    """Clean up test database."""
    import os
    import time

    # Close all database connections
    TestingSessionLocal.close_all()
    engine.dispose()
    # Wait a moment for file handles to release
    time.sleep(0.5)
    try:
        if os.path.exists("./test_resume.db"):
            os.remove("./test_resume.db")
    except PermissionError:
        pass  # Ignore if still in use
