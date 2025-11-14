"""Tests for Phase 5.3 style explanation endpoint."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models_learning_db import FormProfile


client = TestClient(app)


@pytest.fixture
def test_profile_no_hint(db_session: Session) -> FormProfile:
    """Create a form profile without style_hint for testing."""
    profile = FormProfile(
        host="example.com",
        schema_hash="abc123",
        fields={"email": "email", "name": "full_name"},
        style_hint=None,  # No hint yet
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


@pytest.fixture
def test_profile_with_stats(db_session: Session) -> FormProfile:
    """Create a form profile with complete style_hint for testing."""
    profile = FormProfile(
        host="boards.greenhouse.io",
        schema_hash="xyz789",
        fields={"email": "email", "first_name": "first_name"},
        style_hint={
            "preferred_style_id": "style_b",
            "source": "form",
            "segment_key": "signup",
            "style_stats": {
                "style_a": {
                    "source": "form",
                    "segment_key": "signup",
                    "total_runs": 10,
                    "helpful": 3,
                    "unhelpful": 7,
                    "helpful_ratio": 0.3,
                    "avg_edit_chars": 15.5,
                },
                "style_b": {
                    "source": "form",
                    "segment_key": "signup",
                    "total_runs": 12,
                    "helpful": 10,
                    "unhelpful": 2,
                    "helpful_ratio": 0.83,
                    "avg_edit_chars": 2.1,
                },
            },
        },
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


def test_explain_style_no_profile(db_session: Session):
    """Test explanation when no FormProfile exists yet."""
    response = client.get(
        "/api/extension/learning/explain-style",
        params={"host": "unknown.com", "schema_hash": "unknown"},
        headers={"X-Dev-Mode": "true"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["host"] == "unknown.com"
    assert data["schema_hash"] == "unknown"
    assert data["source"] == "none"
    assert data["chosen_style_id"] is None
    assert data["segment_key"] is None
    assert "No style_hint is available yet" in data["explanation"]
    assert data["considered_styles"] == []


def test_explain_style_no_hint(test_profile_no_hint: FormProfile):
    """Test explanation when profile exists but has no style_hint."""
    response = client.get(
        "/api/extension/learning/explain-style",
        params={
            "host": test_profile_no_hint.host,
            "schema_hash": test_profile_no_hint.schema_hash,
        },
        headers={"X-Dev-Mode": "true"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["host"] == "example.com"
    assert data["schema_hash"] == "abc123"
    assert data["source"] == "none"
    assert data["chosen_style_id"] is None
    assert "No style_hint is available yet" in data["explanation"]
    assert data["considered_styles"] == []


def test_explain_style_with_stats(test_profile_with_stats: FormProfile):
    """Test explanation when profile has complete style_hint with stats."""
    response = client.get(
        "/api/extension/learning/explain-style",
        params={
            "host": test_profile_with_stats.host,
            "schema_hash": test_profile_with_stats.schema_hash,
        },
        headers={"X-Dev-Mode": "true"},
    )

    assert response.status_code == 200
    data = response.json()

    # Check basic fields
    assert data["host"] == "boards.greenhouse.io"
    assert data["schema_hash"] == "xyz789"
    assert data["source"] == "form"
    assert data["chosen_style_id"] == "style_b"
    assert data["segment_key"] == "signup"
    assert data["host_family"] == "greenhouse"

    # Check considered styles
    assert len(data["considered_styles"]) == 2

    # Find winner (should be style_b)
    winner = next(s for s in data["considered_styles"] if s["is_winner"])
    assert winner["style_id"] == "style_b"
    assert winner["total_runs"] == 12
    assert winner["helpful_runs"] == 10
    assert winner["unhelpful_runs"] == 2
    assert winner["helpful_ratio"] == 0.83
    assert winner["avg_edit_chars"] == 2.1
    assert winner["source"] == "form"
    assert winner["segment_key"] == "signup"

    # Find loser (should be style_a)
    loser = next(s for s in data["considered_styles"] if not s["is_winner"])
    assert loser["style_id"] == "style_a"
    assert loser["total_runs"] == 10
    assert loser["helpful_ratio"] == 0.3

    # Check explanation contains key info
    assert "style_b" in data["explanation"]
    assert "form" in data["explanation"].lower()
    assert "signup" in data["explanation"]


def test_explain_style_requires_dev_mode():
    """Test that endpoint requires dev mode."""
    response = client.get(
        "/api/extension/learning/explain-style",
        params={"host": "example.com", "schema_hash": "abc123"},
        # No X-Dev-Mode header
    )

    # Should return 403 Forbidden
    assert response.status_code == 403
